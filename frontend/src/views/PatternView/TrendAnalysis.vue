<template>
  <div class="trend-analysis-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>📈 趋势分析 & 热门股追踪</span>
          <el-button type="primary" @click="startScan" :loading="loading">🚀 开始扫描</el-button>
        </div>
      </template>
      
      <div class="filter-section">
        <el-row :gutter="20">
          <el-col :span="12">
            <span class="label">扫描样本数量:</span>
            <el-slider v-model="scanLimit" :min="10" :max="100" :step="10" show-input />
          </el-col>
          <el-col :span="12">
            <span class="label">最低评分筛选:</span>
            <el-slider v-model="minScore" :min="0" :max="100" show-input />
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <div class="results-section" v-if="results.length > 0">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-table 
              :data="results" 
              style="width: 100%" 
              height="500" 
              highlight-current-row
              @current-change="handleCurrentChange"
            >
              <el-table-column prop="ts_code" label="代码" width="100" />
              <el-table-column prop="name" label="名称" width="100" />
              <el-table-column prop="score" label="评分" width="80">
                <template #default="scope">
                  <el-tag :type="getScoreTagType(scope.row.score)">{{ scope.row.score }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-col>
          
          <el-col :span="16">
            <div v-if="selectedStock" class="stock-detail">
              <div class="detail-header">
                <h3>{{ selectedStock.name }} ({{ selectedStock.ts_code }})</h3>
                <el-tag class="industry-tag">{{ selectedStock.industry }}</el-tag>
                <span class="price">最新收盘: {{ selectedStock.latest_close }}</span>
              </div>
              
              <div class="signals-list">
                <h4>触发信号:</h4>
                <el-tag v-for="signal in selectedStock.signals" :key="signal" type="success" class="signal-tag">
                  ✅ {{ signal }}
                </el-tag>
              </div>
              
              <div class="chart-container" v-loading="chartLoading">
                <div ref="chartRef" style="width: 100%; height: 400px;"></div>
              </div>
            </div>
            <div v-else class="empty-selection">
              <el-empty description="请选择左侧股票查看详情" />
            </div>
          </el-col>
        </el-row>
      </div>
      <div v-else-if="!loading && hasScanned" class="empty-results">
        <el-empty description="未找到符合条件的股票" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import axios from 'axios'

// State
const scanLimit = ref(30)
const minScore = ref(30)
const loading = ref(false)
const chartLoading = ref(false)
const hasScanned = ref(false)
const results = ref<any[]>([])
const selectedStock = ref<any>(null)
const chartRef = ref<HTMLElement | null>(null)
let myChart: echarts.ECharts | null = null

// Methods
const getScoreTagType = (score: number) => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'info'
}

const startScan = async () => {
  loading.value = true
  hasScanned.value = false
  results.value = []
  selectedStock.value = null
  
  try {
    // Call backend API
    // Assuming axios base URL is configured or proxy is set up
    const response = await axios.get('/api/trend/scan', {
      params: {
        limit: scanLimit.value,
        min_score: minScore.value
      }
    })
    
    results.value = response.data
    hasScanned.value = true
    
    if (results.value.length > 0) {
      ElMessage.success(`找到 ${results.value.length} 只潜在热门股票`)
    }
  } catch (error) {
    console.error('Scan error:', error)
    ElMessage.error('扫描失败: ' + (error as any).message)
  } finally {
    loading.value = false
  }
}

const handleCurrentChange = async (val: any) => {
  if (!val) return
  selectedStock.value = val
  chartLoading.value = true
  
  try {
    const response = await axios.get(`/api/trend/chart/${val.ts_code}`)
    const data = response.data
    
    await nextTick()
    initChart(data, val.name)
  } catch (error) {
    console.error('Chart error:', error)
    ElMessage.error('加载图表失败')
  } finally {
    chartLoading.value = false
  }
}

const initChart = (data: any, name: string) => {
  if (chartRef.value) {
    if (myChart) {
      myChart.dispose()
    }
    myChart = echarts.init(chartRef.value)
    
    const option = {
      title: {
        text: `${name} K线图`
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        }
      },
      legend: {
        data: ['K线', 'MA5', 'MA10', 'MA20']
      },
      grid: [
        {
          left: '10%',
          right: '10%',
          bottom: '20%',
          height: '60%'
        },
        {
          left: '10%',
          right: '10%',
          bottom: '5%',
          height: '10%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: data.dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          splitNumber: 20,
          min: 'dataMin',
          max: 'dataMax'
        },
        {
          type: 'category',
          gridIndex: 1,
          data: data.dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          min: 'dataMin',
          max: 'dataMax'
        }
      ],
      yAxis: [
        {
          scale: true,
          splitArea: {
            show: true
          }
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLabel: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false }
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: 50,
          end: 100
        },
        {
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          bottom: 10,
          start: 50,
          end: 100
        }
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: data.open.map((o: number, i: number) => [o, data.close[i], data.low[i], data.high[i]]),
          itemStyle: {
            color: '#ec0000',
            color0: '#00da3c',
            borderColor: '#8A0000',
            borderColor0: '#008F28'
          }
        },
        {
          name: 'MA5',
          type: 'line',
          data: data.ma5,
          smooth: true,
          lineStyle: { opacity: 0.5 }
        },
        {
          name: 'MA10',
          type: 'line',
          data: data.ma10,
          smooth: true,
          lineStyle: { opacity: 0.5 }
        },
        {
          name: 'MA20',
          type: 'line',
          data: data.ma20,
          smooth: true,
          lineStyle: { opacity: 0.5 }
        },
        {
          name: 'Vol',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: data.vol,
          itemStyle: {
            color: (params: any) => {
              const i = params.dataIndex;
              return data.close[i] > data.open[i] ? '#ec0000' : '#00da3c';
            }
          }
        }
      ]
    }
    
    myChart.setOption(option)
  }
}

// Resize chart on window resize
window.addEventListener('resize', () => {
  myChart?.resize()
})
</script>

<style scoped>
.trend-analysis-container {
  padding: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filter-section {
  margin-bottom: 20px;
}
.label {
  display: inline-block;
  margin-bottom: 10px;
  font-weight: bold;
}
.detail-header {
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.industry-tag {
  margin-right: 10px;
}
.price {
  font-weight: bold;
  font-size: 1.1em;
}
.signals-list {
  margin-bottom: 20px;
}
.signal-tag {
  margin-right: 10px;
  margin-bottom: 5px;
}
.empty-selection, .empty-results {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 400px;
}
</style>
