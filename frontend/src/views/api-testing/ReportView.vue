<template>
  <div class="report-view">
    <div class="header">
      <h3>{{ $t('apiTesting.report.title') }}</h3>
      <div class="actions">
        <el-button type="primary" @click="refreshReports">{{ $t('apiTesting.report.refreshReport') }}</el-button>
        <el-button @click="openAllureReport">{{ $t('apiTesting.report.viewAllureReport') }}</el-button>
        <el-button type="danger" :disabled="selectedIds.length === 0" @click="handleBatchDelete">批量删除</el-button>
      </div>
    </div>

    <div class="content">
      <el-table :data="reports" v-loading="loading" style="width: 100%" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="test_suite_name" :label="$t('apiTesting.report.testSuite')" min-width="200" />
        <el-table-column prop="status" :label="$t('apiTesting.common.status')" width="120">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_requests" :label="$t('apiTesting.report.totalRequests')" width="100" />
        <el-table-column prop="passed_requests" :label="$t('apiTesting.report.passedCount')" width="100">
          <template #default="scope">
            <span style="color: #67c23a">{{ scope.row.passed_requests }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="failed_requests" :label="$t('apiTesting.report.failedCount')" width="100">
          <template #default="scope">
            <span style="color: #f56c6c">{{ scope.row.failed_requests }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="executed_by.username" :label="$t('apiTesting.report.executor')" width="120" />
        <el-table-column prop="created_at" :label="$t('apiTesting.report.executionTime')" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('apiTesting.common.operation')" width="200">
          <template #default="scope">
            <el-button link type="primary" :loading="generatingId === scope.row.id" :disabled="generatingId !== null" @click="viewReportDetail(scope.row)">{{ $t('apiTesting.report.generateAndViewReport') }}</el-button>
            <el-button link type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'
import api from '@/utils/api'
import dayjs from 'dayjs'

const { t } = useI18n()
const reports = ref([])
const loading = ref(false)
const generatingId = ref(null)
const selectedIds = ref([])

const handleSelectionChange = (selection) => {
  selectedIds.value = selection.map(item => item.id)
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定删除该测试报告？', '提示', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
  }).then(async () => {
    try {
      await api.delete(`/api-testing/test-executions/${row.id}/`)
      ElMessage.success('删除成功')
      loadReports()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const handleBatchDelete = () => {
  if (selectedIds.value.length === 0) return
  ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 条测试报告？`, '提示', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
  }).then(async () => {
    try {
      await api.delete('/api-testing/test-executions/batch-delete/', { data: { ids: selectedIds.value } })
      ElMessage.success('批量删除成功')
      selectedIds.value = []
      loadReports()
    } catch (error) {
      ElMessage.error('批量删除失败')
    }
  }).catch(() => {})
}

const loadReports = async () => {
  loading.value = true
  try {
    const response = await api.get('/api-testing/test-executions/')
    reports.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.loadReports'))
  } finally {
    loading.value = false
  }
}

const refreshReports = async () => {
  await loadReports()
}

const generateAndOpenAllureReport = async (executionId) => {
  if (generatingId.value !== null) return
  generatingId.value = executionId
  try {
    // 调用API生成Allure报告数据
    const response = await api.post(`/api-testing/test-executions/${executionId}/generate-allure-report/`)
    ElMessage.success(t('apiTesting.messages.success.reportGenerated'))

    // 通过当前窗口的origin构造完整的URL，确保通过Vite代理访问
    const fullUrl = `${window.location.origin}${response.data.report_url}`;
    window.open(fullUrl, '_blank')
  } catch (error) {
    ElMessage.error(t('apiTesting.messages.error.reportGenerateFailed'))
  } finally {
    generatingId.value = null
  }
}

const openAllureReport = () => {
  // 提示用户需要先选择一个执行记录来生成报告
  ElMessage.info(t('apiTesting.report.selectExecutionTip'))
}

const viewReportDetail = (report) => {
  // 生成并打开Allure报告
  generateAndOpenAllureReport(report.id)
}

const getStatusType = (status) => {
  const typeMap = {
    'PENDING': 'info',
    'RUNNING': 'warning',
    'COMPLETED': 'success',
    'FAILED': 'danger',
    'CANCELLED': 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const statusKey = {
    'PENDING': 'pending',
    'RUNNING': 'running',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'CANCELLED': 'cancelled'
  }[status]
  return statusKey ? t(`apiTesting.report.status.${statusKey}`) : status
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.report-view {
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h3 {
  margin: 0;
  color: #303133;
}

.content {
  flex: 1;
  overflow: auto;
}
</style>