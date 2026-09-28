<template>
  <div class="unified-projects">
    <!-- 顶部标题与新建按钮 -->
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('project.unifiedTitle') }}</h2>
        <p class="page-subtitle">{{ $t('project.unifiedSubtitle') }}</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        {{ $t('project.newProject') }}
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">{{ $t('project.totalProjects') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value stat-active">{{ stats.active }}</div>
        <div class="stat-label">{{ $t('project.activeProjects') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value stat-completed">{{ stats.completed }}</div>
        <div class="stat-label">{{ $t('project.completed') }}</div>
      </div>
    </div>

    <!-- 过滤工具栏 -->
    <div class="filter-bar">
      <el-input
        v-model="searchText"
        :placeholder="$t('project.searchName')"
        clearable
        style="width: 280px"
        @input="handleSearch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="statusFilter" :placeholder="$t('project.statusFilter')" clearable style="width: 160px" @change="handleFilter">
        <el-option :label="$t('project.active')" value="active" />
        <el-option :label="$t('project.paused')" value="paused" />
        <el-option :label="$t('project.completed')" value="completed" />
        <el-option :label="$t('project.archived')" value="archived" />
      </el-select>
    </div>

    <!-- 项目列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="projects" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" :label="$t('project.projectName')" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="openDetail(row)">{{ row.name }}</el-link>
          </template>
        </el-table-column>
        <el-table-column :label="$t('project.owner')" width="140">
          <template #default="{ row }">{{ row.owner?.username || '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('project.memberCount')" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info" round>{{ row.member_count ?? 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('project.status')" width="110">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('project.createdAt')" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="$t('project.actions')" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openDetail(row)">{{ $t('project.viewDetail') }}</el-button>
            <el-button
              v-if="row.can_manage"
              size="small"
              link
              type="primary"
              @click="openMember(row)"
            >{{ $t('project.manageMember') }}</el-button>
            <el-button v-if="row.can_manage" size="small" link type="primary" @click="openEdit(row)">{{ $t('common.edit') }}</el-button>
            <el-button v-if="row.can_manage" size="small" link type="danger" @click="deleteProject(row)">{{ $t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 新建 / 编辑项目对话框 -->
    <el-dialog
      v-model="showFormDialog"
      :title="editing ? $t('project.editProject') : $t('project.createProject')"
      width="600px"
      :close-on-click-modal="false"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item :label="$t('project.projectName')" prop="name">
          <el-input v-model="form.name" :placeholder="$t('project.projectNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('project.projectDescription')" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" :placeholder="$t('project.projectDescriptionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('project.status')" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option :label="$t('project.active')" value="active" />
            <el-option :label="$t('project.paused')" value="paused" />
            <el-option :label="$t('project.completed')" value="completed" />
            <el-option :label="$t('project.archived')" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isSuperuser" :label="$t('project.owner')">
          <el-select v-model="form.owner_id" filterable clearable style="width: 100%" :placeholder="$t('apiTesting.project.selectOwner')">
            <el-option v-for="u in users" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('project.selectMembers')">
          <el-select v-model="form.member_ids" multiple filterable style="width: 100%" :placeholder="$t('project.selectMembers')">
            <el-option v-for="u in users" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFormDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">
          {{ editing ? $t('project.update') : $t('project.create') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 项目详情 / 成员管理抽屉 -->
    <el-drawer
      v-model="showDetail"
      :title="current?.name || ''"
      size="560px"
      :destroy-on-close="false"
    >
      <template v-if="current">
        <el-descriptions :column="1" border class="detail-desc">
          <el-descriptions-item :label="$t('project.owner')">{{ current.owner?.username || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="$t('project.status')">
            <el-tag :type="getStatusType(current.status)">{{ getStatusText(current.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item :label="$t('project.createdAt')">{{ formatDate(current.created_at) }}</el-descriptions-item>
          <el-descriptions-item :label="$t('project.projectDescription')">{{ current.description || $t('project.noDescription') }}</el-descriptions-item>
        </el-descriptions>

        <div class="member-section">
          <div class="member-header">
            <span class="member-title">{{ $t('project.projectMembers') }}</span>
            <el-button v-if="current.can_manage" size="small" type="primary" @click="openAddMember">
              <el-icon><Plus /></el-icon>
              {{ $t('project.addProjectMember') }}
            </el-button>
          </div>

          <el-table :data="memberRows" v-loading="loadingMembers" size="default">
            <el-table-column prop="username" :label="$t('project.username')" min-width="110">
              <template #default="{ row }">
                <span>{{ row.username }}</span>
                <el-tag v-if="row.role === 'owner'" size="small" type="warning" style="margin-left: 6px">{{ $t('project.owner') }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('project.memberRole')" width="120">
              <template #default="{ row }">
                <el-select
                  v-if="current.can_manage && row.role !== 'owner'"
                  :model-value="row.role"
                  size="small"
                  @change="(v) => changeRole(row, v)"
                >
                  <el-option v-for="r in memberRoleOptions" :key="r.value" :label="r.label" :value="r.value" />
                </el-select>
                <span v-else>{{ getRoleText(row.role) }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('project.actions')" width="80" align="center">
              <template #default="{ row }">
                <el-button
                  v-if="current.can_manage && row.role !== 'owner'"
                  size="small"
                  link
                  type="danger"
                  @click="removeMember(row)"
                >{{ $t('common.delete') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </el-drawer>

    <!-- 添加成员对话框 -->
    <el-dialog v-model="showAddMemberDialog" :title="$t('project.addProjectMember')" width="460px">
      <el-form label-width="90px">
        <el-form-item :label="$t('project.selectMembers')">
          <el-select v-model="addForm.user_id" filterable style="width: 100%" :placeholder="$t('project.selectMembers')">
            <el-option v-for="u in addableUsers" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('project.selectMemberRole')">
          <el-select v-model="addForm.role" style="width: 100%">
            <el-option v-for="r in memberRoleOptions" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddMemberDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submitAddMember">{{ $t('project.addMember') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import api from '@/utils/api'
import { fetchAll } from '@/utils/pagination'
import dayjs from 'dayjs'

const { t } = useI18n()
const userStore = useUserStore()

const loading = ref(false)
const submitting = ref(false)
const projects = ref([])
const users = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchText = ref('')
const statusFilter = ref('')

const showFormDialog = ref(false)
const editing = ref(null)
const formRef = ref()
const form = reactive({
  name: '',
  description: '',
  status: 'active',
  owner_id: null,
  member_ids: []
})

const showDetail = ref(false)
const current = ref(null)
const loadingMembers = ref(false)
const showAddMemberDialog = ref(false)
const addForm = reactive({ user_id: null, role: 'tester' })

const isSuperuser = computed(() => !!userStore.user?.is_superuser)

const rules = computed(() => ({
  name: [
    { required: true, message: t('project.projectNameRequired'), trigger: 'blur' },
    { min: 2, max: 200, message: t('project.projectNameLength'), trigger: 'blur' }
  ],
  status: [{ required: true, message: t('project.projectStatusRequired'), trigger: 'change' }]
}))

const memberRoleOptions = [
  { value: 'admin', label: t('project.roleAdmin') },
  { value: 'developer', label: t('project.roleDeveloper') },
  { value: 'tester', label: t('project.roleTester') },
  { value: 'viewer', label: t('project.roleViewer') }
]

const stats = reactive({ total: 0, active: 0, completed: 0 })

const getRoleText = (role) => {
  const map = {
    owner: t('project.roleOwner'),
    admin: t('project.roleAdmin'),
    developer: t('project.roleDeveloper'),
    tester: t('project.roleTester'),
    viewer: t('project.roleViewer'),
    superuser: t('project.roleSuperuser')
  }
  return map[role] || role
}

const getStatusType = (s) => ({
  active: 'success', paused: 'warning', completed: 'info', archived: 'info'
}[s] || 'info')

const getStatusText = (s) => ({
  active: t('project.active'),
  paused: t('project.paused'),
  completed: t('project.completed'),
  archived: t('project.archived')
}[s] || s)

const formatDate = (d) => (d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-')

const fetchProjects = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      search: searchText.value,
      status: statusFilter.value
    }
    const res = await api.get('/projects/', { params })
    projects.value = res.data.results
    total.value = res.data.count
  } catch (e) {
    ElMessage.error(t('project.fetchListFailed'))
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  try {
    const res = await api.get('/projects/all/')
    const list = res.data || []
    stats.total = list.length
    stats.active = list.filter((p) => p.status === 'active').length
    stats.completed = list.filter((p) => p.status === 'completed').length
  } catch (e) {
    // 统计失败不阻塞页面
  }
}

const fetchUsers = async () => {
  try {
    users.value = await fetchAll('/users/')
  } catch (e) {
    users.value = []
  }
}

const handleSearch = () => { currentPage.value = 1; fetchProjects() }
const handleFilter = () => { currentPage.value = 1; fetchProjects() }
const handlePageChange = () => fetchProjects()

const openCreate = () => {
  editing.value = null
  Object.assign(form, { name: '', description: '', status: 'active', owner_id: null, member_ids: [] })
  showFormDialog.value = true
}

const openEdit = async (row) => {
  editing.value = row
  try {
    // 拉取最新详情，确保成员/负责人与抽屉里的管理保持一致
    const res = await api.get(`/projects/${row.id}/`)
    const p = res.data
    Object.assign(form, {
      name: p.name,
      description: p.description || '',
      status: p.status,
      owner_id: p.owner?.id ?? null,
      member_ids: (p.members || []).map((m) => m.user.id)
    })
  } catch (e) {
    // 失败时回退到行数据
    Object.assign(form, {
      name: row.name,
      description: row.description || '',
      status: row.status,
      owner_id: row.owner?.id ?? null,
      member_ids: (row.members || []).map((m) => m.user.id)
    })
  }
  showFormDialog.value = true
}

const resetForm = () => {
  formRef.value?.clearValidate()
}

const submitForm = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const data = { ...form }
    if (!isSuperuser.value) delete data.owner_id
    if (editing.value) {
      // 编辑时同步成员（按多选框对账：加新成员、移除取消勾选的成员）
      const payload = {
        name: data.name,
        description: data.description,
        status: data.status,
        member_ids: data.member_ids || []
      }
      if (isSuperuser.value) payload.owner_id = data.owner_id
      await api.put(`/projects/${editing.value.id}/`, payload)
      ElMessage.success(t('project.updateSuccess'))
    } else {
      await api.post('/projects/', data)
      ElMessage.success(t('project.createSuccess'))
    }
    showFormDialog.value = false
    fetchProjects()
    fetchStats()
  } catch (e) {
    ElMessage.error(editing.value ? t('project.updateFailed') : t('project.createFailed'))
  } finally {
    submitting.value = false
  }
}

const deleteProject = async (row) => {
  try {
    await ElMessageBox.confirm(t('project.deleteConfirm'), t('common.warning'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })
    await api.delete(`/projects/${row.id}/`)
    ElMessage.success(t('project.deleteSuccess'))
    fetchProjects()
    fetchStats()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(t('project.deleteFailed'))
  }
}

// 成员管理
const memberRows = computed(() => {
  if (!current.value) return []
  const ownerRow = current.value.owner
    ? [{ username: current.value.owner.username, email: current.value.owner.email, role: 'owner', member_id: null }]
    : []
  const memberRows = (current.value.members || []).map((m) => ({
    username: m.user?.username || m.user?.id,
    email: m.user?.email,
    role: m.role,
    member_id: m.id
  }))
  return [...ownerRow, ...memberRows]
})

const addableUsers = computed(() => {
  const existing = new Set(memberRows.value.map((m) => m.username))
  return users.value.filter((u) => !existing.has(u.username))
})

const openDetail = async (row) => {
  current.value = row
  showDetail.value = true
  await refreshDetail()
}

const openMember = (row) => openDetail(row)

const refreshDetail = async () => {
  if (!current.value) return
  loadingMembers.value = true
  try {
    const res = await api.get(`/projects/${current.value.id}/`)
    current.value = res.data
  } catch (e) {
    ElMessage.error(t('project.fetchDetailFailed'))
  } finally {
    loadingMembers.value = false
  }
}

const openAddMember = () => {
  addForm.user_id = null
  addForm.role = 'tester'
  showAddMemberDialog.value = true
}

const submitAddMember = async () => {
  if (!addForm.user_id) {
    ElMessage.warning(t('project.selectUserFirst'))
    return
  }
  submitting.value = true
  try {
    await api.post(`/projects/${current.value.id}/members/add/`, {
      user_id: addForm.user_id,
      role: addForm.role
    })
    ElMessage.success(t('project.addMemberSuccess'))
    showAddMemberDialog.value = false
    await refreshDetail()
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || t('project.addMemberFailed'))
  } finally {
    submitting.value = false
  }
}

const changeRole = async (row, role) => {
  try {
    await api.put(`/projects/${current.value.id}/members/${row.member_id}/role/`, { role })
    ElMessage.success(t('project.roleUpdateSuccess'))
    await refreshDetail()
  } catch (e) {
    ElMessage.error(t('project.roleUpdateFailed'))
  }
}

const removeMember = async (row) => {
  try {
    await ElMessageBox.confirm(`${t('project.removeMember')}: ${row.username}?`, t('common.warning'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })
    await api.delete(`/projects/${current.value.id}/members/${row.member_id}/`)
    ElMessage.success(t('project.memberDeleteSuccess'))
    await refreshDetail()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(t('project.memberDeleteFailed'))
  }
}

onMounted(() => {
  fetchProjects()
  fetchStats()
  fetchUsers()
})
</script>

<style scoped lang="scss">
.unified-projects {
  padding: 4px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;

  .page-title {
    margin: 0 0 4px;
    color: #303133;
    font-size: 20px;
  }

  .page-subtitle {
    margin: 0;
    color: #909399;
    font-size: 13px;
  }
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;

  .stat-card {
    background: #fff;
    border-radius: 10px;
    padding: 18px 20px;
    box-shadow: 0 1px 4px rgba(0, 21, 41, 0.06);

    .stat-value {
      font-size: 28px;
      font-weight: 600;
      color: #303133;

      &.stat-active { color: #67c23a; }
      &.stat-completed { color: #909399; }
    }

    .stat-label {
      margin-top: 4px;
      color: #909399;
      font-size: 13px;
    }
  }
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.table-card {
  border-radius: 10px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.detail-desc {
  margin-bottom: 20px;
}

.member-section {
  .member-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    .member-title {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
    }
  }
}
</style>
