# -*- coding: utf-8 -*-

from ansible.playbook import PlayBook
from ansible import callbacks, utils


def playbook_run(inventory, playbook, default_user=None, default_port=None, default_pri_key_path=None):
    stats = callbacks.AggregateStats()
    playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
    runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)
    # run the playbook
    print default_user, default_port, default_pri_key_path, inventory, playbook
    if default_user and default_port and default_pri_key_path:
        playbook = PlayBook(host_list=inventory,
                            playbook=playbook,
                            forks=5,
                            remote_user=default_user,
                            remote_port=default_port,
                            private_key_file=default_pri_key_path,
                            callbacks=playbook_cb,
                            runner_callbacks=runner_cb,
                            stats=stats,
                            become=True,
                            become_user='root')
    else:
        playbook = PlayBook(host_list=inventory,
                            playbook=playbook,
                            forks=5,
                            callbacks=playbook_cb,
                            runner_callbacks=runner_cb,
                            stats=stats,
                            become=True,
                            become_user='root')
    results = playbook.run()
    print results
    results_r = {'unreachable': [], 'failures': [], 'success': []}
    for hostname, result in results.items():
        if result.get('unreachable', 2):
            results_r['unreachable'].append(hostname)
            print "%s >>> unreachable" % hostname
        elif result.get('failures', 2):
            results_r['failures'].append(hostname)
            print "%s >>> Failed" % hostname
        else:
            results_r['success'].append(hostname)
            print "%s >>> Success" % hostname
    return results_r

