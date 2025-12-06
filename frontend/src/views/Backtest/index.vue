<template>
  <div class="backtest-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <h1 class="page-title">
            <el-icon class="title-icon"><DataLine /></el-icon>
            策略回测
          </h1>
          <p class="page-description">
            验证交易策略在历史数据上的表现
          </p>
        </div>
      </div>
    </div>

    <!-- 回测配置区域 -->
    <div class="backtest-container">
      <el-row :gutter="24">
        <!-- 左侧：回测参数配置 -->
        <el-col :span="18">
          <el-card class="main-form-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>回测参数</h3>
                <el-tag type="info" size="small">必填信息</el-tag>
              </div>
            </template>

            <el-form :model="backtestForm" label-width="120px" class="backtest-form">
              <!-- 策略选择 -->
              <div class="form-section">
                <h4 class="section-title">📈 策略选择</h4>
                <el-form-item label="选择策略" required>
                  <el-select v-model="backtestForm.strategy" placeholder="请选择回测策略" size="large" style="width: 100%">
                    <el-option label="均线交叉策略" value="ma_cross" />
                    <el-option label="RSI超买超卖" value="rsi_overbought_oversold" />
                    <el-option label="自定义策略" value="custom" />
                  </el-select>
                </el-form-item>
                <el-form-item v-if="backtestForm.strategy === 'custom'" label="自定义策略代码" required>
                  <el-input
                    v-model="backtestForm.customStrategyCode"
                    type="textarea"
                    :rows="8"
                    placeholder="请输入自定义策略的Python代码"
                  />
                </el-form-item>
              </div>

              <!-- 股票池选择 -->
              <div class="form-section">
                <h4 class="section-title">🎯 股票池</h4>
                <el-form-item label="选择股票" required>
                  <el-input
                    v-model="backtestForm.symbols"
                    type="textarea"
                    :rows="4"
                    placeholder="请输入股票代码，每行一个，如：000001.SZ, AAPL"
                  />
                </el-form-item>
              </div>

              <!-- 时间范围 -->
              <div class="form-section">
                <h4 class="section-title">📅 时间范围</h4>
                <el-form-item label="开始日期" required>
                  <el-date-picker
                    v-model="backtestForm.startDate"
                    type="date"
                    placeholder="选择回测开始日期"
                    size="large"
                    style="width: 100%"
                  />
                </el-form-item>
                <el-form-item label="结束日期" required>
                  <el-date-picker
                    v-model="backtestForm.endDate"
                    type="date"
                    placeholder="选择回测结束日期"
                    size="large"
                    style="width: 100%"
                  />
                </el-form-item>
              </div>

              <!-- 初始资金 -->
              <div class="form-section">
                <h4 class="section-title">💰 资金设置</h4>
                <el-form-item label="初始资金" required>
                  <el-input-number
                    v-model="backtestForm.initialCapital"
                    :min="1000"
                    :step="1000"
                    size="large"
                    style="width: 100%"
                  />
                </el-form-item>
              </div>

              <!-- 操作按钮 -->
              <div class="form-section">
                <div class="action-buttons" style="display: flex; justify-content: center; align-items: center; width: 100%; text-align: center;">
                  <el-button
                    type="primary"
                    size="large"
                    @click="startBacktest"
                    :loading="backtesting"
                    :disabled="!isFormValid"
                    class="submit-btn large-backtest-btn"
                    style="width: 280px; height: 56px; font-size: 18px; font-weight: 700; border-radius: 16px;"
                  >
                    <el-icon><TrendCharts /></el-icon>
                    开始回测
                  </el-button>
                </div>
              </div>
            </el-form>
          </el-card>
        </el-col>

        <!-- 右侧：回测结果概览 -->
        <el-col :span="6">
          <el-card class="config-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <h3>回测结果概览</h3>
              </div>
            </template>
            <div class="config-content">
              <p v-if="!backtestResult">暂无回测结果</p>
              <div v-else>
                <p><strong>总收益率:</strong> {{ backtestResult.totalReturn }}%</p>
                <p><strong>年化收益率:</strong> {{ backtestResult.annualizedReturn }}%</p>
                <p><strong>最大回撤:</strong> {{ backtestResult.maxDrawdown }}%</p>
                <p><strong>夏普比率:</strong> {{ backtestResult.sharpeRatio }}</p>
                <p><strong>交易次数:</strong> {{ backtestResult.tradeCount }}</p>
                <!-- 更多结果展示 -->
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 回测结果详情 -->
    <div v-if="backtestResult" class="backtest-results-detail" style="margin-top: 24px;">
      <el-card shadow="hover">
        <template #header>
          <div class="card-header">
            <h3>回测结果详情</h3>
          </div>
        </template>
        <el-tabs v-model="activeResultTab">
          <el-tab-pane label="收益曲线" name="equity_curve">
            <div class="chart-container">
              <!-- 收益曲线图表 -->
              <p>这里将展示收益曲线图</p>
            </div>
          </el-tab-pane>
          <el-tab-pane label="交易明细" name="trade_details">
            <el-table :data="backtestResult.tradeDetails" style="width: 100%">
              <el-table-column prop="date" label="日期" width="180" />
              <el-table-column prop="symbol" label="股票代码" width="120" />
              <el-table-column prop="action" label="操作" width="80" />
              <el-table-column prop="price" label="价格" width="100" />
              <el-table-column prop="quantity" label="数量" width="100" />
              <el-table-column prop="pnl" label="盈亏" />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="风险指标" name="risk_metrics">
            <p>这里将展示详细的风险指标</p>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { DataLine, TrendCharts } from '@element-plus/icons-vue'

// 表单数据
const backtestForm = reactive({
  strategy: '',
  customStrategyCode: '',
  symbols: '',
  startDate: null,
  endDate: null,
  initialCapital: 100000,
})

// 回测状态
const backtesting = ref(false)
const backtestResult = ref<any>(null) // 存储回测结果
const activeResultTab = ref('equity_curve') // 默认显示收益曲线

// 表单验证
const isFormValid = computed(() => {
  if (!backtestForm.strategy) return false
  if (backtestForm.strategy === 'custom' && !backtestForm.customStrategyCode.trim()) return false
  if (!backtestForm.symbols.trim()) return false
  if (!backtestForm.startDate || !backtestForm.endDate) return false
  if (backtestForm.startDate && backtestForm.endDate && backtestForm.startDate > backtestForm.endDate) return false
  return true
})

// 开始回测
const startBacktest = async () => {
  if (!isFormValid.value) {
    ElMessage.warning('请填写所有必填项并确保日期范围有效')
    return
  }

  backtesting.value = true
  backtestResult.value = null // 清空上次结果

  try {
    // 模拟API调用
    console.log('开始回测，参数:', backtestForm)
    await new Promise(resolve => setTimeout(resolve, 2000)) // 模拟网络请求

    // 模拟回测结果
    backtestResult.value = {
      totalReturn: (Math.random() * 100 - 20).toFixed(2),
      annualizedReturn: (Math.random() * 30 - 10).toFixed(2),
      maxDrawdown: (Math.random() * 20 + 5).toFixed(2),
      sharpeRatio: (Math.random() * 2).toFixed(2),
      tradeCount: Math.floor(Math.random() * 100) + 10,
      tradeDetails: [
        { date: '2023-01-05', symbol: '000001.SZ', action: '买入', price: 10.50, quantity: 100, pnl: 0 },
        { date: '2023-01-10', symbol: '000001.SZ', action: '卖出', price: 11.20, quantity: 100, pnl: 70 },
        { date: '2023-02-01', symbol: 'AAPL', action: '买入', price: 150.00, quantity: 10, pnl: 0 },
        { date: '2023-02-15', symbol: 'AAPL', action: '卖出', price: 155.00, quantity: 10, pnl: 50 },
      ],
      // 更多结果...
    }
    ElMessage.success('回测完成！')
  } catch (error) {
    console.error('回测失败:', error)
    ElMessage.error('回测失败，请检查策略或参数')
  } finally {
    backtesting.value = false
  }
}
</script>

<style lang="scss" scoped>
.backtest-page {
  min-height: 100vh;
  background: var(--el-bg-color-page);
  padding: 24px;

  .page-header {
    margin-bottom: 32px;

    .header-content {
      background: var(--el-bg-color);
      padding: 32px;
      border-radius: 16px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }

    .title-section {
      .page-title {
        font-size: 28px;
        font-weight: bold;
        color: var(--el-text-color-primary);
        display: flex;
        align-items: center;
        margin-bottom: 8px;

        .title-icon {
          font-size: 32px;
          margin-right: 10px;
          color: var(--el-color-primary);
        }
      }

      .page-description {
        font-size: 16px;
        color: var(--el-text-color-regular);
        margin-left: 42px; // Align with title
      }
    }
  }

  .backtest-container {
    margin-top: 24px;
  }

  .main-form-card, .config-card {
    border-radius: 12px;
    margin-bottom: 24px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      h3 {
        font-size: 18px;
        font-weight: bold;
        color: var(--el-text-color-primary);
      }
    }

    .form-section {
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--el-border-color-lighter);

      &:last-child {
        border-bottom: none;
        padding-bottom: 0;
        margin-bottom: 0;
      }

      .section-title {
        font-size: 16px;
        font-weight: bold;
        color: var(--el-text-color-regular);
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
      }
    }

    .action-buttons {
      margin-top: 24px;
    }
  }

  .backtest-results-detail {
    .chart-container {
      min-height: 300px;
      display: flex;
      justify-content: center;
      align-items: center;
      background-color: var(--el-fill-color-light);
      color: var(--el-text-color-secondary);
      border-radius: 8px;
    }
  }
}
</style>
