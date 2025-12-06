<template>
  <div class="tags-management">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h3>标签管理</h3>
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            新建标签
          </el-button>
        </div>
      </template>

      <el-table :data="tags" v-loading="loading" style="width: 100%">
        <el-table-column label="标签名称" width="200">
          <template #default="{ row }">
            <el-tag :color="row.color" effect="dark" :style="{ borderColor: row.color }">
              {{ row.name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="color" label="颜色代码" width="150">
          <template #default="{ row }">
            <div class="color-preview">
              <div class="color-box" :style="{ backgroundColor: row.color }"></div>
              <span>{{ row.color }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="100" sortable />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editTag(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteTag(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑标签' : '新建标签'"
      width="500px"
    >
      <el-form :model="form" label-width="80px" :rules="rules" ref="formRef">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入标签名称" />
        </el-form-item>
        <el-form-item label="颜色" prop="color">
          <el-color-picker v-model="form.color" />
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { tagsApi, type TagItem } from '@/api/tags'
import { formatDateTime } from '@/utils/datetime'

const tags = ref<TagItem[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const isEdit = ref(false)
const currentId = ref('')
const formRef = ref()

const form = reactive({
  name: '',
  color: '#409EFF',
  sort_order: 0
})

const rules = {
  name: [
    { required: true, message: '请输入标签名称', trigger: 'blur' },
    { min: 1, max: 30, message: '长度在 1 到 30 个字符', trigger: 'blur' }
  ]
}

const fetchTags = async () => {
  loading.value = true
  try {
    const res = await tagsApi.list()
    if (res.success && res.data) {
      tags.value = res.data
    }
  } catch (error) {
    console.error('获取标签失败:', error)
    ElMessage.error('获取标签失败')
  } finally {
    loading.value = false
  }
}

const showCreateDialog = () => {
  isEdit.value = false
  currentId.value = ''
  form.name = ''
  form.color = '#409EFF'
  form.sort_order = 0
  dialogVisible.value = true
}

const editTag = (row: TagItem) => {
  isEdit.value = true
  currentId.value = row.id
  form.name = row.name
  form.color = row.color
  form.sort_order = row.sort_order
  dialogVisible.value = true
}

const deleteTag = async (row: TagItem) => {
  try {
    await ElMessageBox.confirm(`确定要删除标签 "${row.name}" 吗？`, '提示', {
      type: 'warning'
    })
    await tagsApi.remove(row.id)
    ElMessage.success('删除成功')
    fetchTags()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      submitting.value = true
      try {
        if (isEdit.value) {
          await tagsApi.update(currentId.value, form)
          ElMessage.success('更新成功')
        } else {
          await tagsApi.create(form)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchTags()
      } catch (error: any) {
        console.error('提交失败:', error)
        ElMessage.error(error.message || '提交失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

onMounted(() => {
  fetchTags()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.color-preview {
  display: flex;
  align-items: center;
  gap: 8px;
}
.color-box {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
}
</style>
