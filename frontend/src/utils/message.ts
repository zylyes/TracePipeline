import { ElMessage, type MessageHandler } from 'element-plus'

type MessageArgs = Parameters<typeof ElMessage>
type MessageOptions = MessageArgs[0]

interface TrackedMessage {
  handler: MessageHandler
  count: number
  el: HTMLElement | null
  badgeEl: HTMLElement | null
  timer: ReturnType<typeof setTimeout> | null
}

const messageMap = new Map<string, TrackedMessage>()

function getOptionKey(options: any): string {
  if (typeof options === 'string') return `info:${options}`
  const type = options.type || 'info'
  const msg = typeof options.message === 'string' ? options.message : String(options.message ?? '')
  return `${type}:${msg}`
}

function getOptionObj(options: any): Record<string, unknown> & { type?: string; message?: string; duration?: number } {
  if (typeof options === 'string') return { message: options, type: 'info' }
  return { ...options } as Record<string, unknown> & { type?: string; message?: string; duration?: number }
}

function updateBadge(tracked: TrackedMessage) {
  if (!tracked.badgeEl) return
  if (tracked.count <= 1) {
    tracked.badgeEl.style.display = 'none'
  } else {
    tracked.badgeEl.textContent = String(tracked.count)
    tracked.badgeEl.style.display = ''
  }
}

function createBadge(el: HTMLElement): HTMLElement {
  const badge = document.createElement('span')
  badge.className = 'tp-msg-badge'
  badge.style.display = 'none'
  el.appendChild(badge)
  return badge
}

function cleanup(key: string) {
  const tracked = messageMap.get(key)
  if (!tracked) return
  if (tracked.timer) clearTimeout(tracked.timer)
  if (tracked.badgeEl && tracked.badgeEl.parentNode) {
    tracked.badgeEl.parentNode.removeChild(tracked.badgeEl)
  }
  messageMap.delete(key)
}

export function showMessage(options: MessageOptions, duration?: number): MessageHandler {
  const key = getOptionKey(options)
  const existing = messageMap.get(key)

  if (existing) {
    existing.count++
    updateBadge(existing)
    if (existing.timer) clearTimeout(existing.timer)
    const dur = duration ?? 3000
    if (dur > 0) {
      existing.timer = setTimeout(() => {
        existing.handler.close()
        cleanup(key)
      }, dur)
    }
    return existing.handler
  }

  const opts = getOptionObj(options)
  opts.duration = 0

  const handler = ElMessage(opts as any)

  const tracked: TrackedMessage = {
    handler,
    count: 1,
    el: null,
    badgeEl: null,
    timer: null,
  }

  const msgText = typeof opts.message === 'string' ? opts.message : String(opts.message ?? '')

  const checkEl = () => {
    if (tracked.el) return
    const msgEls = document.querySelectorAll('.el-message')
    for (const msgEl of msgEls) {
      if ((msgEl as HTMLElement).querySelector('.tp-msg-badge')) continue
      const contentP = msgEl.querySelector('.el-message__content')
      if (contentP && contentP.textContent === msgText) {
        tracked.el = msgEl as HTMLElement
        tracked.badgeEl = createBadge(tracked.el)
        break
      }
    }
  }

  requestAnimationFrame(() => requestAnimationFrame(checkEl))

  const dur = duration ?? 3000
  if (dur > 0) {
    tracked.timer = setTimeout(() => {
      handler.close()
      cleanup(key)
    }, dur)
  }

  const origClose = handler.close
  handler.close = () => {
    origClose()
    cleanup(key)
  }

  messageMap.set(key, tracked)
  return handler
}

export const msg = {
  success: (message: string, duration?: number) => showMessage({ type: 'success', message }, duration),
  warning: (message: string, duration?: number) => showMessage({ type: 'warning', message }, duration),
  error: (message: string, duration?: number) => showMessage({ type: 'error', message }, duration),
  info: (message: string, duration?: number) => showMessage({ type: 'info', message }, duration),
}
