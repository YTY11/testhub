<template>
  <div class="jenkins-build-page">
    <!-- 筛选 -->
    <el-card shadow="never">
      <el-form :inline="true" :model="store.queryParams">
        <el-form-item label="项目">
          <el-input v-model="store.queryParams.project_name" placeholder="项目名称" clearable style="width: 150px" />
        </el-form-item>

        <el-form-item label="Job 名称">
          <el-input v-model="store.queryParams.job_name" placeholder="Job 名称" clearable style="width: 150px" />
        </el-form-item>

        <el-form-item label="源码分支">
          <el-input v-model="store.queryParams.branch" placeholder="如 test" clearable style="width: 120px" />
        </el-form-item>

        <el-form-item label="环境">
          <el-select v-model="store.queryParams.deploy_env" placeholder="全部" clearable style="width: 100px">
            <el-option label="test" value="test" />
            <el-option label="pro" value="pro" />
            <el-option label="dev" value="dev" />
          </el-select>
        </el-form-item>

        <el-form-item label="触发类型">
          <el-select v-model="store.queryParams.trigger_type" placeholder="全部" clearable style="width: 120px">
            <el-option label="自动发版" value="auto" />
            <el-option label="手动发布" value="manual" />
          </el-select>
        </el-form-item>

        <el-form-item label="结果">
          <el-select v-model="store.queryParams.build_result" placeholder="全部" clearable style="width: 110px">
            <el-option label="成功" value="SUCCESS" />
            <el-option label="失败" value="FAILURE" />
            <el-option label="中止" value="ABORTED" />
            <el-option label="不稳定" value="UNSTABLE" />
            <el-option label="构建中" value="BUILDING" />
          </el-select>
        </el-form-item>

        <el-form-item label="开始时间">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始"
            end-placeholder="结束"
            style="width: 230px"
            @change="handleDateChange"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button type="success" @click="openDialog()">新增记录</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格 -->
    <el-card shadow="never" style="margin-top: 12px">
      <!-- 工具栏 -->
      <div class="table-toolbar">
        <div class="left">
          <el-button
            type="danger"
            :disabled="selectedIds.length === 0"
            @click="handleBatchDelete"
          >
            批量删除
            <span v-if="selectedIds.length > 0">（{{ selectedIds.length }}）</span>
          </el-button>
        </div>
        <div class="right">
          <span v-if="selectedIds.length > 0" class="selected-tip">
            已选 {{ selectedIds.length }} 项
            <el-button link type="primary" size="small" @click="clearSelection">清空</el-button>
          </span>
        </div>
      </div>

      <el-table
        ref="tableRef"
        :data="store.buildList"
        v-loading="store.loading"
        border
        stripe
        row-key="id"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" align="center" />

        <!-- <el-table-column prop="id" label="ID" width="70" /> -->
        <el-table-column label="序号" width="70" align="center">
          <template #default="scope">
            {{ scope.$index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="project_name" label="项目" width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <div>{{ row.project_name }}</div>
            <div v-if="row.project_display_name" class="sub-text">{{ row.project_display_name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="job_name" label="Job 名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="build_number" label="构建号" width="90" align="center">
          <template #default="{ row }">#{{ row.build_number }}</template>
        </el-table-column>
        <el-table-column label="触发" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.trigger_type === 'auto'" type="success" size="small">自动</el-tag>
            <el-tag v-else-if="row.trigger_type === 'manual'" type="warning" size="small">手动</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="resultTagType(row.build_result)" effect="dark" size="small">
              {{ resultLabel(row.build_result) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="branch" label="源码分支" width="110" show-overflow-tooltip />
        <el-table-column prop="release_branch" label="发布分支" width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.release_branch || '-' }}</template>
        </el-table-column>
        <el-table-column prop="deploy_env" label="环境" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.deploy_env" size="small" effect="plain">{{ row.deploy_env }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="commit_sha" label="Commit" width="100">
          <template #default="{ row }">
            <el-tooltip v-if="row.commit_sha" :content="row.commit_sha" placement="top">
              <span>{{ row.commit_sha.substring(0, 7) }}</span>
            </el-tooltip>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="变更内容" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.change_content || '-' }}</template>
        </el-table-column>
        <el-table-column label="开始时间" width="170">
          <template #default="{ row }">{{ formatTime(row.start_time) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="170">
          <template #default="{ row }">{{ formatTime(row.end_time) }}</template>
        </el-table-column>
        <el-table-column label="持续" width="100" align="center">
          <template #default="{ row }">{{ formatDuration(row.duration_ms) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
            <el-button link type="warning" size="small" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="store.queryParams.page"
          v-model:page-size="store.queryParams.page_size"
          :total="store.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSearch"
          @current-change="handleSearch"
        />
      </div>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="构建详情" size="600px">
      <el-descriptions :column="1" border v-if="current">
        <el-descriptions-item label="项目">
          {{ current.project_name }}
          <span v-if="current.project_display_name">（{{ current.project_display_name }}）</span>
        </el-descriptions-item>
        <el-descriptions-item label="Job 名称">{{ current.job_name }}</el-descriptions-item>
        <el-descriptions-item label="构建号">#{{ current.build_number }}</el-descriptions-item>
        <el-descriptions-item label="触发类型">
          {{ current.trigger_type === 'auto' ? '自动发版' : current.trigger_type === 'manual' ? '手动发布' : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="结果">
          <el-tag :type="resultTagType(current.build_result)" effect="dark" size="small">
            {{ resultLabel(current.build_result) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="构建链接">
          <a v-if="current.build_url" :href="current.build_url" target="_blank">{{ current.build_url }}</a>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="源码分支">{{ current.branch || '-' }}</el-descriptions-item>
        <el-descriptions-item label="发布分支">{{ current.release_branch || '-' }}</el-descriptions-item>
        <el-descriptions-item label="部署环境">{{ current.deploy_env || '-' }}</el-descriptions-item>
        <el-descriptions-item label="Commit SHA">{{ current.commit_sha || '-' }}</el-descriptions-item>
        <el-descriptions-item label="变更内容">
          <pre class="pre-wrap">{{ current.change_content || '-' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="变更文件">
          <pre class="pre-wrap">{{ current.change_files || '-' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ formatTime(current.start_time) }}</el-descriptions-item>
        <el-descriptions-item label="结束时间">{{ formatTime(current.end_time) }}</el-descriptions-item>
        <el-descriptions-item label="持续时间">{{ formatDuration(current.duration_ms) }}</el-descriptions-item>
        <el-descriptions-item label="触发人">{{ current.triggered_by || '-' }}</el-descriptions-item>
        <el-descriptions-item label="主流水线">
          <span v-if="current.parent_job_name">
            {{ current.parent_job_name }} #{{ current.parent_build_number }}
          </span>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="备注">{{ current.remark || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑构建记录' : '新增构建记录'" width="720px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="110px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="项目名称" prop="project_name">
              <el-input v-model="form.project_name" placeholder="如 screen3-web" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="项目显示名">
              <el-input v-model="form.project_display_name" placeholder="如 正式 3.0 前端" />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="Job 名称" prop="job_name">
              <el-input v-model="form.job_name" placeholder="如 platform-screen-web" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="构建号" prop="build_number">
              <el-input-number v-model="form.build_number" :min="1" style="width: 100%" />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="构建结果" prop="build_result">
              <el-select v-model="form.build_result" style="width: 100%">
                <el-option label="成功" value="SUCCESS" />
                <el-option label="失败" value="FAILURE" />
                <el-option label="中止" value="ABORTED" />
                <el-option label="不稳定" value="UNSTABLE" />
                <el-option label="构建中" value="BUILDING" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="触发类型">
              <el-select v-model="form.trigger_type" clearable style="width: 100%">
                <el-option label="自动发版" value="auto" />
                <el-option label="手动发布" value="manual" />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="源码分支">
              <el-input v-model="form.branch" placeholder="如 test" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发布分支">
              <el-input v-model="form.release_branch" placeholder="如 release-2025.09" />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="部署环境">
              <el-select v-model="form.deploy_env" clearable style="width: 100%">
                <el-option label="test" value="test" />
                <el-option label="pro" value="pro" />
                <el-option label="dev" value="dev" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Commit SHA">
              <el-input v-model="form.commit_sha" placeholder="可选" />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="form.start_time"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                clearable
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="form.end_time"
                type="datetime"
                value-format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                clearable
              />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item label="持续时间(ms)">
              <el-input-number v-model="form.duration_ms" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="构建链接">
              <el-input v-model="form.build_url" placeholder="可选" />
            </el-form-item>
          </el-col>

          <el-col :span="24">
            <el-form-item label="变更内容">
              <el-input v-model="form.change_content" type="textarea" :rows="3" />
            </el-form-item>
          </el-col>

          <el-col :span="24">
            <el-form-item label="变更文件">
              <el-input v-model="form.change_files" type="textarea" :rows="3" />
            </el-form-item>
          </el-col>

          <el-col :span="24">
            <el-form-item label="备注">
              <el-input v-model="form.remark" type="textarea" :rows="2" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useJenkinsStore } from '@/stores/jenkins'
import {
  getJenkinsBuild, createJenkinsBuild, updateJenkinsBuild,
  deleteJenkinsBuild, batchDeleteJenkinsBuilds
} from '@/api/jenkins'

const store = useJenkinsStore()

// ---------- 详情 ----------
const detailVisible = ref(false)
const current = ref(null)

// ---------- 新增 / 编辑 ----------
const dialogVisible = ref(false)
const formRef = ref(null)
const dateRange = ref([])

// ---------- 多选 ----------
const tableRef = ref(null)
const selectedRows = ref([])
const selectedIds = computed(() => selectedRows.value.map(r => r.id))

const defaultForm = () => ({
  id: null, project_name: '', project_display_name: '',
  job_name: '', build_number: 1, build_url: '',
  build_result: 'SUCCESS', branch: '', release_branch: '',
  deploy_env: 'test', trigger_type: '',
  start_time: '', end_time: '', duration_ms: 0,
  commit_sha: '', change_content: '', change_files: '',
  triggered_by: '', parent_job_name: '', parent_build_number: null,
  remark: ''
})
const form = reactive(defaultForm())

const rules = {
  project_name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  job_name: [{ required: true, message: '请输入 Job 名称', trigger: 'blur' }],
  build_number: [{ required: true, message: '请输入构建号', trigger: 'blur' }],
  build_result: [{ required: true, message: '请选择构建结果', trigger: 'change' }]
}

onMounted(() => store.fetchBuildList())

// ---------- 查询 / 重置 ----------
function handleSearch() { store.fetchBuildList() }
function handleReset() {
  store.resetQuery()
  dateRange.value = []
  store.fetchBuildList()
}
function handleDateChange(val) {
  store.queryParams.start_date = val?.[0] || ''
  store.queryParams.end_date = val?.[1] || ''
}

// ---------- 详情 ----------
function openDetail(row) {
  current.value = row
  detailVisible.value = true
}

// ---------- 新增 / 编辑 ----------
function openDialog(row) {
  Object.assign(form, defaultForm())
  if (row) {
    getJenkinsBuild(row.id).then(res => Object.assign(form, res.data))
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  await formRef.value.validate()
  const payload = { ...form }
  delete payload.id

  // 空时间转 null
  if (!payload.start_time) payload.start_time = null
  if (!payload.end_time) payload.end_time = null
  if (payload.parent_build_number === '' || payload.parent_build_number === undefined) {
    payload.parent_build_number = null
  }

  // 其它空值统一转空字符串
  ;['project_display_name', 'build_url', 'branch', 'release_branch',
    'deploy_env', 'commit_sha', 'change_content', 'change_files',
    'triggered_by', 'trigger_type', 'parent_job_name', 'remark'].forEach(k => {
    if (payload[k] === undefined || payload[k] === null) payload[k] = ''
  })

  try {
    if (form.id) {
      await updateJenkinsBuild(form.id, payload)
      ElMessage.success('更新成功')
    } else {
      await createJenkinsBuild(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    store.fetchBuildList()
  } catch (err) {
    showBackendErrors(err)
  }
}

// 把后端字段错误友好展示
function showBackendErrors(err) {
  const data = err?.response?.data
  if (!data || typeof data !== 'object') {
    ElMessage.error(err?.message || '操作失败')
    return
  }
  const msgs = []
  Object.keys(data).forEach(k => {
    const v = data[k]
    if (Array.isArray(v)) msgs.push(`${k}: ${v.join('；')}`)
    else msgs.push(`${k}: ${v}`)
  })
  ElMessage.error(msgs.join('；') || '操作失败')
}

// ---------- 单条删除 ----------
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除「${row.project_name} - ${row.job_name} #${row.build_number}」？`,
      '提示', { type: 'warning' }
    )
    await deleteJenkinsBuild(row.id)
    ElMessage.success('删除成功')
    clearSelection()
    store.fetchBuildList()
  } catch (e) { /* 取消 */ }
}

// ---------- 多选 ----------
function handleSelectionChange(rows) {
  selectedRows.value = rows
}
function clearSelection() {
  tableRef.value?.clearSelection()
  selectedRows.value = []
}

// ---------- 批量删除 ----------
async function handleBatchDelete() {
  if (selectedIds.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedIds.value.length} 条构建记录吗？删除后不可恢复。`,
      '批量删除',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
  } catch (e) {
    return  // 用户取消
  }

  try {
    const res = await batchDeleteJenkinsBuilds(selectedIds.value)
    const { deleted, not_found } = res.data
    if (not_found && not_found.length > 0) {
      ElMessage.warning(`成功删除 ${deleted} 条，${not_found.length} 条未找到`)
    } else {
      ElMessage.success(`成功删除 ${deleted} 条`)
    }
    clearSelection()
    store.fetchBuildList()
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || '批量删除失败')
  }
}

// ---------- 工具函数 ----------
function resultLabel(r) {
  return {
    SUCCESS: '成功', FAILURE: '失败', ABORTED: '中止',
    UNSTABLE: '不稳定', BUILDING: '构建中'
  }[r] || r
}
function resultTagType(r) {
  return {
    SUCCESS: 'success', FAILURE: 'danger', ABORTED: 'info',
    UNSTABLE: 'warning', BUILDING: 'primary'
  }[r] || 'info'
}
function formatDuration(ms) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}min`
  return `${(ms / 3600000).toFixed(2)}h`
}
function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.selected-tip {
  color: #666;
  font-size: 13px;
}
.sub-text {
  color: #999;
  font-size: 12px;
}
.pre-wrap {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: inherit;
}
</style>