<template>
  <div class="pattern-view">
    <!-- 页面标题区域 - 参考AnalysisHistory.vue的page-header结构 -->
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><CreditCard /></el-icon>
        模式挖掘
      </h1>
      <p class="page-description">
        发现市场中的重复模式和交易机会
      </p>
    </div>

    <!-- 操作按钮区域 - 参考其他页面的按钮布局 -->
    <el-card class="action-card" shadow="never">
      <div class="action-buttons">
        <el-button type="primary" @click="showMiningPanel = true" size="large">
          <el-icon><Search /></el-icon>
          开始挖掘
        </el-button>
        <el-button type="success" @click="showScanPanel = true" size="large">
          <el-icon><Aim /></el-icon>
          扫描机会
        </el-button>
      </div>
    </el-card>

    <!-- 主要内容区域 -->
    <div class="main-content">
      <!-- 挖掘结果展示 -->
      <div v-if="miningResult" class="result-section">
        <el-card class="result-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">📈 挖掘结果</span>
              <el-button type="text" @click="miningResult = null">关闭</el-button>
            </div>
          </template>
          <div class="result-content">
            <div class="result-stats">
              <el-statistic title="发现模式数量" :value="miningResult.pattern_count || 0" />
              <el-statistic title="平均相似度" :value="((miningResult.avg_similarity || 0) * 100).toFixed(1)" suffix="%" />
              <el-statistic title="处理时间" :value="miningResult.processing_time || 0" suffix="秒" />
            </div>
            
            <div v-if="miningResult.templates && miningResult.templates.length > 0" class="templates-section">
              <h4>生成的模板:</h4>
              <el-table :data="miningResult.templates" style="width: 100%">
                <el-table-column prop="pattern_id" label="模式ID" width="120" />
                <el-table-column prop="name" label="名称" />
                <el-table-column prop="count" label="出现次数" width="100" />
                <el-table-column prop="success_rate" label="成功率" width="100">
                  <template #default="scope">
                    {{ ((scope.row.success_rate || 0) * 100).toFixed(1) }}%
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 扫描结果展示 -->
      <div v-if="scanResult && scanResult.length > 0" class="result-section">
        <el-card class="result-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">🎯 潜在机会</span>
              <el-button type="text" @click="scanResult = []">关闭</el-button>
            </div>
          </template>
          <el-table :data="scanResult" style="width: 100%">
            <el-table-column prop="symbol" label="股票代码" width="120" />
            <el-table-column prop="pattern_name" label="匹配模式" />
            <el-table-column prop="similarity" label="相似度" width="100">
              <template #default="scope">
                {{ (scope.row.similarity * 100).toFixed(1) }}%
              </template>
            </el-table-column>
            <el-table-column prop="expected_return" label="预期收益" width="100">
              <template #default="scope">
                {{ (scope.row.expected_return * 100).toFixed(1) }}%
              </template>
            </el-table-column>
            <el-table-column prop="confidence" label="置信度" width="100">
              <template #default="scope">
                {{ (scope.row.confidence * 100).toFixed(1) }}%
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button type="text" size="small" @click="viewPatternDetails(scope.row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <!-- 默认空状态 -->
      <div v-if="!miningResult && (!scanResult || scanResult.length === 0)" class="empty-state">
        <el-empty description="点击上方按钮开始模式挖掘或扫描潜在机会">
          <template #image>
            <div style="font-size: 64px">🔍</div>
          </template>
        </el-empty>
      </div>
    </div>

    <!-- 模式挖掘抽屉 -->
    <el-drawer
      v-model="showMiningPanel"
      title="🔍 模式挖掘设置"
      direction="rtl"
      size="400px"
      :before-close="handleMiningClose"
    >
      <div class="drawer-content">
        <el-form :model="miningForm" label-width="100px" class="mining-form">
          <el-form-item label="市场选择" required>
            <el-select v-model="miningForm.market" placeholder="选择市场" style="width: 100%">
              <el-option label="A股" value="CN" />
              <el-option label="港股" value="HK" />
              <el-option label="美股" value="US" />
            </el-select>
          </el-form-item>

          <el-form-item label="数据年份" required>
            <el-input-number 
              v-model="miningForm.years" 
              :min="1" 
              :max="10" 
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>

          <el-form-item label="最小样本数">
            <el-input-number 
              v-model="miningForm.min_samples" 
              :min="3" 
              :max="100" 
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>

          <el-form-item>
            <el-button 
              type="primary" 
              @click="startMining" 
              :loading="miningLoading"
              style="width: 100%"
            >
              {{ miningLoading ? '挖掘中...' : '开始挖掘' }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-drawer>

    <!-- 扫描机会抽屉 -->
    <el-drawer
      v-model="showScanPanel"
      title="🎯 扫描潜在机会"
      direction="rtl"
      size="400px"
      :before-close="handleScanClose"
    >
      <div class="drawer-content">
        <el-form :model="scanForm" label-width="100px" class="scan-form">
          <el-form-item label="目标市场" required>
            <el-select v-model="scanForm.market" placeholder="选择市场" style="width: 100%">
              <el-option label="A股" value="CN" />
              <el-option label="港股" value="HK" />
              <el-option label="美股" value="US" />
            </el-select>
          </el-form-item>

          <el-form-item label="相似阈值">
            <el-slider
              v-model="scanForm.similarity_threshold"
              :min="0.5"
              :max="1"
              :step="0.05"
              show-stops
              show-input
            />
          </el-form-item>

          <el-form-item>
            <el-button 
              type="success" 
              @click="scanPatterns" 
              :loading="scanLoading"
              style="width: 100%"
            >
              {{ scanLoading ? '扫描中...' : '开始扫描' }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { CreditCard, Search, Aim } from '@element-plus/icons-vue'

// 表单数据
const miningForm = reactive({
  market: 'CN',
  years: 3,
  min_samples: 10
})

const scanForm = reactive({
  market: 'CN',
  similarity_threshold: 0.7
})

// 状态管理
const showMiningPanel = ref(false)
const showScanPanel = ref(false)
const miningLoading = ref(false)
const scanLoading = ref(false)
const miningResult = ref<any>(null)
const scanResult = ref<any[]>([])

// 方法
const startMining = async () => {
  miningLoading.value = true
  try {
    const response = await fetch(`/api/pattern/mine?market=${miningForm.market}&years=${miningForm.years}`, {
      method: 'POST'
    })
    
    if (!response.ok) {
      throw new Error('挖掘请求失败')
    }
    
    miningResult.value = await response.json()
    showMiningPanel.value = false
    ElMessage.success('模式挖掘完成！')
    
  } catch (error) {
    console.error('模式挖掘失败:', error)
    ElMessage.error('模式挖掘失败，请重试')
  } finally {
    miningLoading.value = false
  }
}

const scanPatterns = async () => {
  scanLoading.value = true
  try {
    const response = await fetch(`/api/pattern/upcoming?market=${scanForm.market}`)
    
    if (!response.ok) {
      throw new Error('扫描请求失败')
    }
    
    scanResult.value = await response.json()
    showScanPanel.value = false
    ElMessage.success('机会扫描完成！')
    
  } catch (error) {
    console.error('机会扫描失败:', error)
    ElMessage.error('机会扫描失败，请重试')
  } finally {
    scanLoading.value = false
  }
}

const handleMiningClose = (done: () => void) => {
  done()
}

const handleScanClose = (done: () => void) => {
  done()
}

const viewPatternDetails = (row: any) => {
  ElMessage.info(`查看模式详情: ${row.pattern_name}`)
}
</script>

<style lang="scss" scoped>
.pattern-view {
  .page-header {
    margin-bottom: 24px;

    .page-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 24px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin: 0 0 8px 0;
    }

    .page-description {
      color: var(--el-text-color-regular);
      margin: 0;
    }
  }

  .action-card {
    margin-bottom: 24px;

    .action-buttons {
      display: flex;
      gap: 16px;
      justify-content: center;
      padding: 16px 0;
    }
  }

  .main-content {
    .result-section {
      margin-bottom: 24px;
    }

    .result-card {
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 600;

        .card-title {
          font-size: 16px;
          color: var(--el-text-color-primary);
        }
      }

      .result-content {
        padding: 16px 0;

        .result-stats {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 24px;
          margin-bottom: 24px;
        }

        .templates-section {
          margin-top: 24px;

          h4 {
            margin: 0 0 16px 0;
            font-size: 16px;
            font-weight: 600;
            color: var(--el-text-color-primary);
          }
        }
      }
    }

    .empty-state {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 400px;
      background: var(--el-fill-color-light);
      border-radius: 8px;
      border: 1px dashed var(--el-border-color);
    }
  }

  .drawer-content {
    padding: 20px;

    .mining-form,
    .scan-form {
      margin-top: 20px;
    }
  }
}
</style>
