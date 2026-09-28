import { defineStore } from 'pinia'
import { getJenkinsBuilds } from '@/api/jenkins'

export const useJenkinsStore = defineStore('jenkins', {
  state: () => ({
    buildList: [],
    total: 0,
    loading: false,
    queryParams: {
      page: 1,
      page_size: 10,
      project_name: '',
      job_name: '',
      branch: '',
      deploy_env: '',
      build_result: '',
      trigger_type: '',
      parent_build_number: '',
      start_date: '',
      end_date: ''
    }
  }),

  actions: {
    async fetchBuildList() {
      this.loading = true
      try {
        const params = {}
        Object.keys(this.queryParams).forEach(k => {
          const v = this.queryParams[k]
          if (v !== '' && v !== null && v !== undefined) params[k] = v
        })
        const res = await getJenkinsBuilds(params)
        this.buildList = res.data.results || res.data
        this.total = res.data.count || this.buildList.length
      } finally {
        this.loading = false
      }
    },
    resetQuery() {
      this.queryParams = {
        page: 1, page_size: 10,
        project_name: '', job_name: '', branch: '',
        deploy_env: '', build_result: '', trigger_type: '',
        parent_build_number: '', start_date: '', end_date: ''
      }
    }
  }
})