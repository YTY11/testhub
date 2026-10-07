// noVNC 调试地址辅助：有头模式执行 UI 测试时，自动在用户端浏览器打开容器桌面调试画面
const VNC_STORAGE_KEY = 'testhub_vnc_url'

export function getVncUrl() {
  try {
    return localStorage.getItem(VNC_STORAGE_KEY) || ''
  } catch (e) {
    return ''
  }
}

export function setVncUrl(url) {
  try {
    localStorage.setItem(VNC_STORAGE_KEY, (url || '').trim())
  } catch (e) { /* ignore */ }
}

export function openVncIfHeaded(headless) {
  // 无头模式不打开；有头模式且已配置 noVNC 地址时，自动打开容器桌面调试画面
  if (headless) return
  const url = getVncUrl()
  if (url) {
    try {
      window.open(url, '_blank')
    } catch (e) { /* ignore */ }
  }
}
