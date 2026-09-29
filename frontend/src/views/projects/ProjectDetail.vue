<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ $t('project.projectDetail') }}</h1>
      <el-button type="primary" @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>
        {{ $t('common.back') }}
      </el-button>
    </div>

    <div class="card-container">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="$t('project.projectInfo')" name="info">
          <div v-if="project">
            <el-descriptions :column="2" border>
              <el-descriptions-item :label="$t('project.projectName')">{{ project.name }}</el-descriptions-item>
              <el-descriptions-item :label="$t('project.status')">
                <el-tag :type="getStatusType(project.status)">{{ getStatusText(project.status) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item :label="$t('project.owner')">{{ project.owner?.username }}</el-descriptions-item>
              <el-descriptions-item :label="$t('project.createdAt')">{{ formatDate(project.created_at) }}</el-descriptions-item>
              <el-descriptions-item :label="$t('project.projectDescription')" :span="2">{{ project.description || $t('project.noDescription') }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="$t('project.projectMembers')" name="members">
          <div class="members-section">
            <el-button type="primary" @click="openAddMember">{{ $t('project.addMember') }}</el-button>
            <el-table :data="project?.members || []" style="width: 100%; margin-top: 20px;">
              <el-table-column prop="user.username" :label="$t('project.username')" />
              <el-table-column prop="user.email" :label="$t('project.email')" />
              <el-table-column prop="role" :label="$t('project.role')" />
              <el-table-column prop="joined_at" :label="$t('project.joinedAt')">
                <template #default="{ row }">
                  {{ formatDate(row.joined_at) }}
                </template>
              </el-table-column>
              <el-table-column :label="$t('project.actions')" width="100">
                <template #default="{ row }">
                  <el-button size="small" type="danger" @click="removeMember(row)">{{ $t('common.delete') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane :label="$t('project.environments')" name="environments">
          <div class="environments-section">
            <el-button type="primary" @click="openAddEnv">{{ $t('project.addEnvironment') }}</el-button>
            <el-table :data="project?.environments || []" style="width: 100%; margin-top: 20px;">
              <el-table-column prop="name" :label="$t('project.environmentName')" />
              <el-table-column prop="base_url" :label="$t('project.baseUrl')" />
              <el-table-column prop="description" :label="$t('project.description')" />
              <el-table-column prop="is_default" :label="$t('project.defaultEnvironment')">
                <template #default="{ row }">
                  <el-tag v-if="row.is_default" type="success">{{ $t('project.yes') }}</el-tag>
                  <span v-else>{{ $t('project.no') }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('project.actions')" width="100">
                <template #default="{ row }">
                  <el-button size="small" type="danger" @click="deleteEnvironment(row)">{{ $t('common.delete') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 添加成员对话框 -->
    <el-dialog v-model="showAddMemberDialog" :title="$t('project.addMember')" width="460px">
      <el-form label-width="90px">
        <el-form-item :label="$t('project.username')">
          <el-select v-model="addForm.user_id" filterable style="width: 100%" :placeholder="$t('project.addMember')">
            <el-option v-for="u in users" :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('project.role')">
          <el-select v-model="addForm.role" style="width: 100%">
            <el-option :label="$t('project.roleAdmin')" value="admin" />
            <el-option :label="$t('project.roleDeveloper')" value="developer" />
            <el-option :label="$t('project.roleTester')" value="tester" />
            <el-option :label="$t('project.roleViewer')" value="viewer" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddMemberDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="addingMember" @click="addMember">{{ $t('project.addMember') }}</el-button>
      </template>
    </el-dialog>

    <!-- 添加环境对话框 -->
    <el-dialog v-model="showAddEnvDialog" :title="$t('project.addEnvironment')" width="480px">
      <el-form :model="addEnvForm" label-width="90px">
        <el-form-item :label="$t('project.environmentName')" required>
          <el-input v-model="addEnvForm.name" :placeholder="$t('project.environmentName')" />
        </el-form-item>
        <el-form-item :label="$t('project.baseUrl')" required>
          <el-input v-model="addEnvForm.base_url" :placeholder="$t('project.baseUrl')" />
        </el-form-item>
        <el-form-item :label="$t('project.description')">
          <el-input v-model="addEnvForm.description" type="textarea" />
        </el-form-item>
        <el-form-item :label="$t('project.defaultEnvironment')">
          <el-switch v-model="addEnvForm.is_default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddEnvDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="addingEnv" @click="addEnvironment">{{ $t('project.addEnvironment') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'
import dayjs from 'dayjs'

const route = useRoute()
const { t } = useI18n()
const project = ref(null)
const activeTab = ref('info')
const showAddMemberDialog = ref(false)
const showAddEnvDialog = ref(false)
const users = ref([])
const addingMember = ref(false)
const addingEnv = ref(false)
const addForm = reactive({
  user_id: null,
  role: 'tester'
})
const addEnvForm = reactive({
  name: '',
  base_url: '',
  description: '',
  is_default: false
})

const fetchProject = async () => {
  try {
    const response = await api.get(`/projects/${route.params.id}/`)
    project.value = response.data
  } catch (error) {
    ElMessage.error(t('project.fetchDetailFailed'))
  }
}

const loadUsers = async () => {
  try {
    const response = await api.get('/users/')
    users.value = response.data.results || response.data || []
  } catch (error) {
    users.value = []
  }
}

const openAddMember = () => {
  addForm.user_id = null
  addForm.role = 'tester'
  showAddMemberDialog.value = true
}

const addMember = async () => {
  if (!addForm.user_id) {
    ElMessage.warning(t('project.selectUserFirst'))
    return
  }
  addingMember.value = true
  try {
    await api.post(`/projects/${route.params.id}/members/add/`, {
      user_id: addForm.user_id,
      role: addForm.role
    })
    ElMessage.success(t('project.addMemberSuccess'))
    showAddMemberDialog.value = false
    fetchProject()
  } catch (error) {
    ElMessage.error(error?.response?.data?.error || t('project.addMemberFailed'))
  } finally {
    addingMember.value = false
  }
}

const openAddEnv = () => {
  Object.assign(addEnvForm, { name: '', base_url: '', description: '', is_default: false })
  showAddEnvDialog.value = true
}

const addEnvironment = async () => {
  if (!addEnvForm.name) {
    ElMessage.warning(t('project.environmentNameRequired'))
    return
  }
  if (!addEnvForm.base_url) {
    ElMessage.warning(t('project.baseUrlRequired'))
    return
  }
  addingEnv.value = true
  try {
    await api.post(`/projects/${route.params.id}/environments/`, { ...addEnvForm })
    ElMessage.success(t('project.environmentAddSuccess'))
    showAddEnvDialog.value = false
    fetchProject()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || t('project.environmentAddFailed'))
  } finally {
    addingEnv.value = false
  }
}

const deleteEnvironment = async (env) => {
  try {
    await api.delete(`/projects/${route.params.id}/environments/${env.id}/`)
    ElMessage.success(t('project.environmentDeleteSuccess'))
    fetchProject()
  } catch (error) {
    ElMessage.error(t('project.environmentDeleteFailed'))
  }
}

const getStatusType = (status) => {
  const typeMap = {
    active: 'success',
    paused: 'warning',
    completed: 'info',
    archived: 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    active: t('project.active'),
    paused: t('project.paused'),
    completed: t('project.completed'),
    archived: t('project.archived')
  }
  return textMap[status] || status
}

const formatDate = (dateString) => {
  return dayjs(dateString).format('YYYY-MM-DD HH:mm')
}

const removeMember = async (member) => {
  try {
    await api.delete(`/projects/${route.params.id}/members/${member.id}/`)
    ElMessage.success(t('project.memberDeleteSuccess'))
    fetchProject()
  } catch (error) {
    ElMessage.error(t('project.memberDeleteFailed'))
  }
}

onMounted(() => {
  fetchProject()
  loadUsers()
})
</script>

<style lang="scss" scoped>
.members-section, .environments-section {
  padding: 20px 0;
}
</style>
