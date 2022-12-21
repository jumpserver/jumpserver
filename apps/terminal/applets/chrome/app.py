import time
from enum import Enum
from subprocess import CREATE_NO_WINDOW

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

from common import (Asset, User, Account, Platform)
from common import (notify_err_message, block_input, unblock_input)
from common import (BaseApplication)


class Command(Enum):
    TYPE = 'type'
    CLICK = 'click'
    OPEN = 'open'


def _execute_type(ele: WebElement, value: str):
    ele.send_keys(value)


def _execute_click(ele: WebElement, value: str):
    ele.click()


commands_func_maps = {
    Command.CLICK: _execute_click,
    Command.TYPE: _execute_type,
    Command.OPEN: _execute_type,
}


class StepAction:
    methods_map = {
        "NAME": By.NAME,
        "ID": By.ID,
        "CLASS_NAME": By.CLASS_NAME,
        "CSS_SELECTOR": By.CSS_SELECTOR,
        "CSS": By.CSS_SELECTOR,
        "XPATH": By.XPATH
    }

    def __init__(self, target='', value='', command=Command.TYPE, **kwargs):
        self.target = target
        self.value = value
        self.command = command

    def execute(self, driver: webdriver.Chrome) -> bool:
        if not self.target:
            return True
        target_name, target_value = self.target.split("=", 1)
        by_name = self.methods_map.get(target_name.upper(), By.NAME)
        ele = driver.find_element(by=by_name, value=target_value)
        if not ele:
            return False
        if self.command == 'type':
            ele.send_keys(self.value)
        elif self.command in ['click', 'button']:
            ele.click()
        elif self.command in ['open']:
            driver.get(self.value)
        return True

    def _execute_command_type(self, ele, value):
        ele.send_keys(value)


def execute_action(driver: webdriver.Chrome, step: StepAction) -> bool:
    try:
        return step.execute(driver)
    except Exception as e:
        print(e)
        notify_err_message(str(e))
        return False


class WebAPP(object):

    def __init__(self, app_name: str = '', user: User = None, asset: Asset = None,
                 account: Account = None, platform: Platform = None, **kwargs):
        self.app_name = app_name
        self.user = user
        self.asset = asset
        self.account = account
        self.platform = platform

        self.extra_data = self.asset.specific
        self._steps = list()
        autofill_type = self.asset.specific.autofill
        if autofill_type == "basic":
            self._steps = self._default_custom_steps()
        elif autofill_type == "script":
            steps = sorted(self.asset.specific.script, key=lambda step_item: step_item['step'])
            for item in steps:
                val = item['value']
                if val:
                    val = val.replace("{USERNAME}", self.account.username)
                    val = val.replace("{SECRET}", self.account.secret)
                item['value'] = val
                self._steps.append(item)

    def _default_custom_steps(self) -> list:
        account = self.account
        specific_property = self.asset.specific
        default_steps = [
            {
                "step": 1,
                "value": account.username,
                "target": specific_property.username_selector,
                "command": "type"
            },
            {
                "step": 2,
                "value": account.secret,
                "target": specific_property.password_selector,
                "command": "type"
            },
            {
                "step": 3,
                "value": "",
                "target": specific_property.submit_selector,
                "command": "click"
            }
        ]
        return default_steps

    def execute(self, driver: webdriver.Chrome) -> bool:
        if not self.asset.address:
            return True

        for step in self._steps:
            action = StepAction(**step)
            ret = execute_action(driver, action)
            if not ret:
                unblock_input()
                notify_err_message(f"执行失败: target: {action.target} command: {action.command}")
                block_input()
                return False
        return True


def default_chrome_driver_options():
    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")
    # 禁用 扩展
    options.add_argument("--disable-extensions")
    # 禁用开发者工具
    options.add_argument("--disable-dev-tools")
    # 禁用 密码管理器弹窗
    prefs = {"credentials_enable_service": False,
             "profile.password_manager_enabled": False}
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ['enable-automation'])
    return options


class AppletApplication(BaseApplication):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver = None
        self.app = WebAPP(app_name=self.app_name, user=self.user,
                          account=self.account, asset=self.asset, platform=self.platform)
        self._chrome_options = default_chrome_driver_options()

    def run(self):
        service = Service()
        #  driver 的 console 终端框不显示
        service.creationflags = CREATE_NO_WINDOW
        self.driver = webdriver.Chrome(options=self._chrome_options, service=service)
        self.driver.implicitly_wait(10)
        if self.app.asset.address != "":
            self.driver.get(self.app.asset.address)
            ok = self.app.execute(self.driver)
            if not ok:
                print("执行失败")
        self.driver.maximize_window()

    def wait(self):
        msg = "Unable to evaluate script: disconnected: not connected to DevTools\n"
        while True:
            time.sleep(5)
            logs = self.driver.get_log('driver')
            if len(logs) == 0:
                continue
            ret = logs[-1]
            if isinstance(ret, dict):
                if ret.get("message") == msg:
                    print(ret)
                    break
        self.close()

    def close(self):
        if self.driver:
            try:
                self.driver.close()
            except Exception as e:
                print(e)
