$(function () {
    const panel = document.getElementById('radius-push')
    if (!panel) return

    const radiusType = panel.dataset.type
    const select = document.getElementById('mfa-select')
    const next = document.getElementById('submit_button')
    const send = document.getElementById('radius-push-send')
    const cancel = document.getElementById('radius-push-cancel')
    const status = document.getElementById('radius-push-status')
    const form = panel.closest('form')
    const csrf = form.elements.csrfmiddlewaretoken.value
    const url = new URL(panel.dataset.url, window.location.origin)
    url.search = window.location.search

    let attempt = panel.dataset.attempt
    let busy = false
    let timer

    function render() {
        next.hidden = select.value === radiusType
        select.disabled = busy || Boolean(attempt)
        send.hidden = Boolean(attempt)
        send.disabled = busy
        cancel.hidden = !attempt
        cancel.disabled = busy
    }

    async function request(action) {
        const endpoint = new URL(url)
        const options = { cache: 'no-store' }
        if (action) {
            options.method = 'POST'
            options.body = new URLSearchParams({ action, attempt, csrfmiddlewaretoken: csrf })
        } else {
            endpoint.searchParams.set('attempt', attempt)
        }
        const response = await fetch(endpoint, options)
        return response.json()
    }

    function show(result) {
        if (result.status === 'session_expired') {
            window.location.assign(panel.dataset.login + window.location.search)
            return
        }
        if (result.status === 'complete') {
            window.location.assign(result.redirect)
            return
        }
        if (result.status === 'approved') {
            attempt = result.attempt
            return act('complete')
        }
        if (result.status === 'pending') {
            attempt = result.attempt
            status.textContent = panel.dataset.pending
            timer = setTimeout(poll, 1500)
        } else {
            attempt = ''
            const messages = {
                rejected: panel.dataset.rejected,
                timed_out: panel.dataset.timedOut,
                cancelled: panel.dataset.cancelled,
                rate_limited: panel.dataset.rateLimited,
            }
            status.textContent = result.message || messages[result.status] || panel.dataset.failed
        }
        render()
    }

    async function poll() {
        const current = attempt
        try {
            const result = await request()
            if (attempt === current && !busy) return show(result)
        } catch {
            if (attempt === current && !busy) show({ status: 'failed' })
        }
    }

    async function act(action) {
        if (busy) return
        busy = true
        clearTimeout(timer)
        render()
        let result
        try {
            result = await request(action)
        } catch {
            result = { status: 'failed' }
        }
        busy = false
        return show(result)
    }

    send.addEventListener('click', () => act('start'))
    cancel.addEventListener('click', () => act('cancel'))
    select.addEventListener('change', render)
    form.addEventListener('submit', event => {
        if (select.value === radiusType) event.preventDefault()
    })

    if (attempt) {
        select.value = radiusType
        selectChange(radiusType, true)
        status.textContent = panel.dataset.pending
        void poll()
    }
    render()
})
