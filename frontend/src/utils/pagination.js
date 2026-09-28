import api from '@/utils/api'

/**
 * 拉取一个分页接口的全部分页数据（自动按 next 翻页直到取完）。
 * 用于树、下拉、选择器等"需要完整数据且无内置翻页器"的场景，
 * 避免默认每页 20 条 / page_size 上限导致数据被截断。
 *
 * @param {string} url          接口路径，如 '/api-testing/requests/'
 * @param {object} params       附加查询参数（会自动叠加 page 分页）
 * @returns {Promise<Array>}    全部分页结果
 */
export async function fetchAll(url, params = {}) {
  let page = 1
  let all = []
  while (true) {
    const res = await api.get(url, { params: { ...params, page } })
    const payload = res.data?.data ?? res.data
    const results = payload?.results || payload || []
    all = all.concat(results)
    if (!payload?.next) break
    page += 1
  }
  return all
}

/**
 * 针对走 api 模块函数（如 getUiProjects(params)）的取数，拉取全部分页数据。
 * 兼容返回体可能带 { data: { results } } 的包装（app-automation 等）。
 *
 * @param {Function} requestFn  如 getUiProjects
 * @param {object}   params     附加查询参数（会自动叠加 page）
 * @returns {Promise<Array>}
 */
export async function fetchAllFn(requestFn, params = {}) {
  let page = 1
  let all = []
  while (true) {
    const res = await requestFn({ ...params, page })
    const payload = res.data?.data ?? res.data
    const results = payload?.results || payload || []
    all = all.concat(results)
    if (!payload?.next) break
    page += 1
  }
  return all
}
