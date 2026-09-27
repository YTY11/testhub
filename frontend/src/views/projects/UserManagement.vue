<template>
  <div class="user-management">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ $t('project.userManageTitle') }}</h2>
        <p class="page-subtitle">{{ $t('project.userManageSubtitle') }}</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        {{ $t('project.newUser') }}
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total }}</div>
        <div class="stat-label">{{ $t('project.userTotal') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value stat-super">{{ stats.superusers }}</div>
        <div class="stat-label">{{ $t('project.superuserTotal') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value stat-disabled">{{ stats.disabled }}</div>
        <div class="stat-label">{{ $t('project.disabledTotal') }}</div>
      </div>
    </div>

    <!-- 用户列表 -->
    <el-card shadow="never" class="table-card">
      <div class="table-title">{{ $t('project.userList') }}</div>
      <el-table :data="users" v-loading="loading" style="width: 100%">
        <el-table-column prop="username" :label="$t('project.usernameLabel')" min-width="130">
          <template #default="{ row }">
            <span>{{ row.username }}</span>
            <el-tag v-if="row.id === currentUserId" size="small" type="info" style="margin-left: 6px">me</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('project.realName')" min-width="110">
          <template #default="{ row }">{{ (row.first_name || row.last_name) ? `${row.first_name}${row.last_name}` : '-' }}</template>
        </el-table-column>
        <el-table-column prop="email" :label="$t('project.email')" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.email || '-' }}</template>
        </el-table-column>
        <el-table-column prop="department" :label="$t('project.departmentLabel')" width="110">
          <template #default="{ row }">{{ row.department || '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('project.roleLabel')" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_superuser ? 'danger' : 'info'">
              {{ row.is_superuser ? $t('project.roleSuperUserLabel') : $t('project.roleNormalUserLabel') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('project.statusLabel')" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? $t('project.enabled') : $t('project.disabled') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('project.registerTime')" width="170">
          <template #default="{ row }">{{ formatDate(row.date_joined) }}</template>
        </el-table-column>
        <el-table-column :label="$t('project.actions')" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openEdit(row)">{{ $t('project.editUser') }}</el-button>
            <el-button size="small" link type="primary" @click="openResetPwd(row)">{{ $t('project.resetPassword') }}</el-button>
            <el-button
              v-if="row.id !== currentUserId"
              size="small"
              link
              :type="row.is_active ? 'danger' : 'success'"
              @click="toggleActive(row)"
            >{{ row.is_active ? $t('project.disabled') : $t('project.enabled') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 角色与权限说明 -->
    <el-card shadow="never" class="role-card">
      <div class="role-title">{{ $t('project.roleExplainTitle') }}</div>
      <div class="role-grid">
        <div class="role-group">
          <div class="role-group-title">{{ $t('project.systemRoleTitle') }}</div>
          <ul>
            <li>{{ $t('project.systemRoleSuperuser') }}</li>
            <li>{{ $t('project.systemRoleNormal') }}</li>
          </ul>
        </div>
        <div class="role-group">
          <div class="role-group-title">{{ $t('project.projectRoleTitle') }}</div>
          <ul>
            <li><el-tag size="small" type="warning" style="margin-right:4px">{{ $t('project.roleOwner') }}</el-tag>{{ $t('project.projectRoleOwner') }}</li>
            <li><el-tag size="small" type="danger" style="margin-right:4px">{{ $t('project.roleAdmin') }}</el-tag>{{ $t('project.projectRoleAdmin') }}</li>
            <li><el-tag size="small" style="margin-right:4px">{{ $t('project.roleDeveloper') }}</el-tag>{{ $t('project.projectRoleDeveloper') }}</li>
            <li><el-tag size="small" type="success" style="margin-right:4px">{{ $t('project.roleTester') }}</el-tag>{{ $t('project.projectRoleTester') }}</li>
            <li><el-tag size="small" type="info" style="margin-right:4px">{{ $t('project.roleViewer') }}</el-tag>{{ $t('project.projectRoleViewer') }}</li>
          </ul>
        </div>
      </div>
    </el-card>

    <!-- 新增 / 编辑用户对话框 -->
    <el-dialog
      v-model="showFormDialog"
      :title="editing ? $t('project.editUser') : $t('project.newUser')"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item :label="$t('project.usernameLabel')" prop="username">
          <el-input v-model="form.username" :disabled="!!editing" />
        </el-form-item>
        <el-form-item :label="$t('project.realName')">
          <el-input v-model="form.first_name" :placeholder="$t('project.realName')" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="email@example.com" />
        </el-form-item>
        <el-form-item v-if="!editing" :label="$t('project.passwordLabel')" prop="password">
          <el-input v-model="form.password" type="password" show-password :placeholder="$t('project.passwordPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('project.departmentLabel')">
          <el-input v-model="form.department" />
        </el-form-item>
        <el-form-item :label="$t('project.positionLabel')">
          <el-input v-model="form.position" />
        </el-form-item>
        <el-form-item :label="$t('project.roleLabel')">
          <el-radio-group v-model="form.is_superuser">
            <el-radio :value="false">{{ $t('project.roleNormalUserLabel') }}</el-radio>
            <el-radio :value="true">{{ $t('project.roleSuperUserLabel') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="editing && editing.id !== currentUserId" :label="$t('project.statusLabel')">
          <el-switch v-model="form.is_active" :active-text="$t('project.enabled')" :inactive-text="$t('project.disabled')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFormDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">
          {{ editing ? $t('project.update') : $t('project.create') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="showPwdDialog" :title="$t('project.resetPasswordTitle')" width="420px">
      <el-form label-width="90px">
        <el-form-item :label="$t('project.newPassword')">
          <el-input v-model="pwdForm.password" type="password" show-password :placeholder="$t('project.passwordPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPwdDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submitResetPwd">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '@/utils/api'
import dayjs from 'dayjs'

const { t } = useI18n()
const userStore = useUserStore()

const currentUserId = computed(() => userStore.user?.id)
const loading = ref(false)
const submitting = ref(false)
const users = ref([])
const showFormDialog = ref(false)
const editing = ref(null)
const formRef = ref()
const showPwdDialog = ref(false)
const pwdTarget = ref(null)

const form = reactive({
  username: '',
  first_name: '',
  email: '',
  password: '',
  department: '',
  position: '',
  is_superuser: false,
  is_active: true
})

const pwdForm = reactive({ password: '' })

const stats = reactive({ total: 0, superusers: 0, disabled: 0 })

const rules = computed(() => ({
  username: [{ required: true, message: t('project.projectNameRequired'), trigger: 'blur' }],
  email: [{ type: 'email', message: 'Email 格式不正确', trigger: 'blur' }],
  password: editing.value
    ? []
    : [{ required: true, min: 6, message: t('project.passwordPlaceholder'), trigger: 'blur' }]
}))

const formatDate = (d) => (d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-')

const fetchUsers = async () => {
  loading.value = true
  try {
    const res = await api.get('/users/manage/')
    users.value = res.data || []
    stats.total = users.value.length
    stats.superusers = users.value.filter((u) => u.is_superuser).length
    stats.disabled = users.value.filter((u) => !u.is_active).length
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || t('project.loadUsersFailed'))
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  editing.value = null
  Object.assign(form, {
    username: '', first_name: '', email: '', password: '',
    department: '', position: '', is_superuser: false, is_active: true
  })
  showFormDialog.value = true
}

const openEdit = (row) => {
  editing.value = row
  Object.assign(form, {
    username: row.username,
    first_name: row.first_name || '',
    email: row.email || '',
    password: '',
    department: row.department || '',
    position: row.position || '',
    is_superuser: !!row.is_superuser,
    is_active: !!row.is_active
  })
  showFormDialog.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (editing.value) {
      const payload = {
        email: form.email,
        first_name: form.first_name,
        department: form.department,
        position: form.position,
        is_superuser: form.is_superuser,
        is_active: form.is_active
      }
      await api.patch(`/users/manage/${editing.value.id}/`, payload)
      ElMessage.success(t('project.userUpdateSuccess'))
    } else {
      await api.post('/users/manage/', { ...form })
      ElMessage.success(t('project.userCreateSuccess'))
    }
    showFormDialog.value = false
    fetchUsers()
  } catch (e) {
    const msg = e?.response?.data?.error
    ElMessage.error(msg || (editing.value ? t('project.userUpdateFailed') : t('project.userCreateFailed')))
  } finally {
    submitting.value = false
  }
}

const openResetPwd = (row) => {
  pwdTarget.value = row
  pwdForm.password = ''
  showPwdDialog.value = true
}

const submitResetPwd = async () => {
  if (!pwdForm.password || pwdForm.password.length < 6) {
    ElMessage.warning(t('project.passwordPlaceholder'))
    return
  }
  submitting.value = true
  try {
    await api.post(`/users/manage/${pwdTarget.value.id}/reset-password/`, { password: pwdForm.password })
    ElMessage.success(t('project.passwordResetSuccess'))
    showPwdDialog.value = false
  } catch (e) {
    ElMessage.error(e?.response?.data?.error || t('project.passwordResetFailed'))
  } finally {
    submitting.value = false
  }
}

const toggleActive = async (row) => {
  const msg = row.is_active ? t('project.confirmDisable') : t('project.confirmEnable')
  try {
    await ElMessageBox.confirm(msg, t('common.warning'), {
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
      type: 'warning'
    })
    await api.patch(`/users/manage/${row.id}/`, { is_active: !row.is_active })
    ElMessage.success(t('project.userUpdateSuccess'))
    fetchUsers()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.error || t('project.userUpdateFailed'))
  }
}

onMounted(fetchUsers)
</script>

<style scoped lang="scss">
.user-management {
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

      &.stat-super { color: #f56c6c; }
      &.stat-disabled { color: #909399; }
    }

    .stat-label {
      margin-top: 4px;
      color: #909399;
      font-size: 13px;
    }
  }
}

.table-card {
  border-radius: 10px;
  margin-bottom: 20px;

  .table-title {
    font-size: 15px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 14px;
  }
}

.role-card {
  border-radius: 10px;

  .role-title {
    font-size: 15px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 14px;
  }

  .role-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;

    @media screen and (max-width: 1024px) {
      grid-template-columns: 1fr;
    }
  }

  .role-group-title {
    font-weight: 600;
    color: #606266;
    margin-bottom: 10px;
  }

  ul {
    margin: 0;
    padding-left: 18px;
    color: #606266;
    line-height: 1.9;
    font-size: 13px;
  }
}
</style>
