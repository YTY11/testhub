import request from '@/utils/api'

// ---------- 列表 / 详情 ----------
export function getJenkinsBuilds(params) {
  return request({ url: '/jenkins-builds/', method: 'get', params })
}
export function getJenkinsBuild(id) {
  return request({ url: `/jenkins-builds/${id}/`, method: 'get' })
}

// ---------- 新增 / 更新 ----------
export function createJenkinsBuild(data) {
  return request({ url: '/jenkins-builds/', method: 'post', data })
}
export function updateJenkinsBuild(id, data) {
  return request({ url: `/jenkins-builds/${id}/`, method: 'put', data })
}
export function patchJenkinsBuild(id, data) {
  return request({ url: `/jenkins-builds/${id}/`, method: 'patch', data })
}

// ---------- 删除 ----------
export function deleteJenkinsBuild(id) {
  return request({ url: `/jenkins-builds/${id}/`, method: 'delete' })
}
export function batchDeleteJenkinsBuilds(ids) {
  return request({
    url: '/jenkins-builds/batch-delete/',
    method: 'post',
    data: { ids }
  })
}