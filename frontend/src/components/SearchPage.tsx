import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PieChart } from '@mui/x-charts/PieChart'
import { BarChart } from '@mui/x-charts/BarChart'
import BananaDropImageLoop from "../components/BananaDrop"
import persona1 from '../assets/1.png'
import persona2 from '../assets/2.png'
import persona3 from '../assets/3.png'
import persona4 from '../assets/4.png'

// Type definitions
interface ConsumerInsight {
  persona_id: string
  insights: {
    likelihood: string
    relevance: string
    intent: string
  }
}

interface ApiData {
  product_description: string
  would_buy_pie: {
    yes: number
    no: number
  }
  yes_pie: Record<string, number>
  age_distribution: Record<string, number>
  consumer_insights: Record<string, ConsumerInsight>
}

function SearchPage() {
  const [searchParams] = useSearchParams()
  const productDescription = searchParams.get('product') || ''

  // Test data for display
  const testData: ApiData = {
  product_description: productDescription, // e.g. "Amazon Echo (5th Gen) smart speaker with Alexa voice assistant"
  would_buy_pie: {
    yes: 720,
    no: 280
  },
  yes_pie: {
    "Smart Home Enthusiast": 300,
    "Busy Professional": 200,
    "Family Household": 140,
    "College Student": 80
  },
  age_distribution: {
    "18-24": 180,
    "25-34": 320,
    "35-44": 260,
    "45-54": 160,
    "55+": 80
  },
  consumer_insights: {
    "Smart Home Enthusiast": {
      persona_id: "P101",
      insights: {
        likelihood: "Very high likelihood to purchase. Already invested in IoT devices and looking to expand ecosystem.",
        relevance: "Extremely relevant — values seamless integration with smart lights, thermostats, and automation routines.",
        intent: "Actively comparing new Echo models and considering adding one to every room for full home control."
      }
    },
    "Busy Professional": {
      persona_id: "P102",
      insights: {
        likelihood: "High likelihood. Appreciates hands-free scheduling, meeting reminders, and smart office integration.",
        relevance: "Highly relevant for productivity and work-life balance — uses Alexa to manage calendars, alarms, and tasks.",
        intent: "Looking for convenience-focused tech to streamline routines. Ready to buy if setup is easy and privacy features are strong."
      }
    },
    "Family Household": {
      persona_id: "P103",
      insights: {
        likelihood: "Moderate to high. Finds appeal in music streaming, timers, and child-friendly voice control.",
        relevance: "Strong relevance for family entertainment and coordination (shopping lists, intercom, parental controls).",
        intent: "Evaluating as a shared device for home use. May purchase during Amazon sales or bundle deals."
      }
    },
    "College Student": {
      persona_id: "P104",
      insights: {
        likelihood: "Moderate likelihood — price-sensitive but curious about tech convenience.",
        relevance: "Relevant for studying, alarms, and streaming. Also useful for controlling dorm room lights and music.",
        intent: "Interested in entry-level Echo models or refurbished options. Influenced by TikTok and peer reviews."
      }
    }
  }
};

  // Empty data structure
  const emptyData: ApiData = {
    product_description: "",
    would_buy_pie: {
      yes: 0,
      no: 0
    },
    yes_pie: {},
    age_distribution: {},
    consumer_insights: {}
  }

  const [data, setData] = useState<ApiData>(emptyData)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const loadData = async () => {
      if (!productDescription) return

      setLoading(true)

      // Simulate loading delay
      await new Promise(resolve => setTimeout(resolve, 5000))

      // Use placeholder data
      setData({ ...testData, product_description: productDescription })
      setLoading(false)
    }

    loadData()
  }, [productDescription])

  // Transform data for charts
  const getWouldBuyData = () => {
    const total = data.would_buy_pie.yes + data.would_buy_pie.no
    const yesPercentage = (data.would_buy_pie.yes / total) * 100
    const noPercentage = (data.would_buy_pie.no / total) * 100

    return [
      { name: 'YES', value: yesPercentage, count: data.would_buy_pie.yes },
      { name: 'NO', value: noPercentage, count: data.would_buy_pie.no }
    ]
  }

  const getAgeDistributionData = () => {
    return Object.entries(data.age_distribution).map(([name, value]) => ({
      name,
      yes: Math.round((value as number) * (data.would_buy_pie.yes / (data.would_buy_pie.yes + data.would_buy_pie.no))),
      no: Math.round((value as number) * (data.would_buy_pie.no / (data.would_buy_pie.yes + data.would_buy_pie.no)))
    }))
  }

  const getConsumerProfiles = () => {
    return Object.entries(data.consumer_insights).map(([name, data]) => ({
      name,
      personaId: data.persona_id,
      insights: data.insights
    }))
  }

  const sharedChartHeight = 260

  // Map persona names to images
  const personaImages: Record<string, string> = {
    "Smart Home Enthusiast": persona1,
    "Busy Professional": persona2,
    "Family Household": persona3,
    "College Student": persona4
  }

  // Loading page
  if (loading) {
    return (
      <div style={{
        backgroundColor: '#ffffff',
        height: '100vh',
        width: '100vw',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        overflow: 'hidden',
        position: 'fixed',
        top: 0,
        left: 0
      }}>
        <h1 style={{
          color: '#000000',
          fontSize: '48px',
          fontWeight: '700',
          letterSpacing: '2px',
          marginBottom: '40px',
          fontFamily: 'Akira, sans-serif'
        }}>
          Mirra
        </h1>
        


        <div style={{
          width: '600px',
          backgroundColor: '#1e1e1e',
          padding: '40px',
          borderRadius: '16px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
          textAlign: 'center'
        }}>
          {/* Animated banana drop */}
          <div style={{ margin: "0 auto 30px" }}>
            <BananaDropImageLoop width={480} height={300} speed={650} />

          </div>

          <h2 style={{
            color: '#ffffff',
            fontSize: '24px',
            fontWeight: '600',
            marginBottom: '15px'
          }}>
            Analyzing Product
          </h2>

          <p style={{
            color: '#b0b0b0',
            fontSize: '16px',
            lineHeight: '1.6',
            marginBottom: '20px'
          }}>
            We're gathering consumer insights for:
          </p>

          <p style={{
            color: '#ff9900',
            fontSize: '18px',
            fontWeight: '600',
            padding: '15px',
            backgroundColor: '#2a2a2a',
            borderRadius: '8px'
          }}>
            {productDescription}
          </p>

          <p style={{
            color: '#888',
            fontSize: '14px',
            marginTop: '25px'
          }}>
            This may take a moment...
          </p>
        </div>

        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    )
  }

  return (
    <div style={{
      backgroundColor: '#ffffff',
      height: '100vh',
      width: '100vw',
      overflow: 'hidden',
      position: 'fixed',
      top: 0,
      left: 0
    }}>
      <div style={{
        height: '100vh',
        overflowY: 'auto',
        padding: '20px 40px',
        fontFamily: 'Satoshi, sans-serif'
      }}>
        <div style={{
          maxWidth: '1400px',
          margin: '0 auto'
        }}>
          {/* Header with Logo and Product */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            marginBottom: '20px',
            gap: '20px'
          }}>
            <h1 style={{
              color: '#000000',
              fontSize: '36px',
              fontWeight: '700',
              letterSpacing: '2px',
              margin: 0,
              fontFamily: 'Akira, sans-serif'
            }}>
              Mirra
            </h1>
            <div>
              <strong style={{ color: '#000000' }}>Product:</strong>
              <span style={{ fontSize: '22px', fontWeight: '900', color: '#ff9900', marginLeft: '8px', fontFamily: 'Satoshi, sans-serif' }}>
                {data.product_description || productDescription}
              </span>
            </div>
          </div>

          {/* Content */}
          <>
      {/* Charts Section */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '25px',
        marginBottom: '25px'
      }}>
        {/* Would Buy Pie Chart */}
        <div style={{
          backgroundColor: '#f2f1ef',
          padding: '15px 25px 25px 25px',
          borderRadius: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.5)'
        }}>
          <h3 style={{ textAlign: 'left', marginBottom: '25px', color: '#000000', marginTop: '0', fontFamily: 'Satoshi, sans-serif', fontWeight: '900' }}>Would Buy?</h3>
          <PieChart
            series={[
              {
                data: getWouldBuyData().map((item) => ({
                  id: item.name,
                  value: item.value,
                  label: `${item.name}: ${item.value.toFixed(1)}%`,
                  color: item.name === 'YES' ? '#ff9900' : '#146eb4'
                })),
                highlightScope: { fade: 'global', highlight: 'item' },
              },
            ]}
            height={250}
            slotProps={{
              legend: {
                direction: 'row' as any,
                position: { vertical: 'bottom', horizontal: 'middle' } as any,
              } as any
            }}
            sx={{
              '& .MuiPieArc-root': { stroke: '#f2f1ef', strokeWidth: 2 },
              '& text': { fill: '#000000 !important', fontWeight: 600 },
              '& .MuiChartsLegend-series text': { fill: '#000000 !important' }
            }}
          />
        </div>

        {/* Personas Stacked Bar Chart */}
        <div style={{
          backgroundColor: '#eed09c',
          padding: '15px 25px 25px 25px',
          borderRadius: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.5)'
        }}>
          <h3 style={{ textAlign: 'left', marginBottom: '25px', color: '#000000', marginTop: '0', fontFamily: 'Satoshi, sans-serif', fontWeight: '900' }}>Personas Distribution</h3>
          <BarChart
            xAxis={[{ scaleType: 'band', data: ['Personas'] }]}
            series={Object.keys(data.yes_pie).map((persona, index) => ({
              data: [data.yes_pie[persona]],
              label: persona,
              stack: 'total',
              color: ['#ff9900', '#146eb4', '#232f3e', '#f2f2f2'][index % 4]
            }))}
            height={sharedChartHeight}
            slotProps={{
              legend: {
                direction: 'row' as any,
                position: { vertical: 'bottom', horizontal: 'middle' } as any,
              } as any
            }}
            sx={{
              '& .MuiChartsAxis-line': { stroke: '#444' },
              '& .MuiChartsAxis-tick': { stroke: '#444' },
              '& .MuiChartsAxis-tickLabel': { fill: '#000000' },
              '& .MuiChartsLegend-series text': { fill: '#000000 !important', fontWeight: 600, fontSize: '14px' }
            }}
          />
        </div>

        {/* Age Distribution Bar Chart with Yes/No */}
        <div style={{
          backgroundColor: '#f9d8b7',
          padding: '15px 25px 25px 25px',
          borderRadius: '12px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.5)'
        }}>
          <h3 style={{ textAlign: 'left', marginBottom: '25px', color: '#000000', marginTop: '0', fontFamily: 'Satoshi, sans-serif', fontWeight: '900' }}>Age Distribution</h3>
          <BarChart
            xAxis={[{ scaleType: 'band', data: getAgeDistributionData().map(d => d.name) }]}
            series={[
              {
                data: getAgeDistributionData().map(d => d.yes),
                label: 'Yes',
                stack: 'total',
                color: '#ff9900'
              },
              {
                data: getAgeDistributionData().map(d => d.no),
                label: 'No',
                stack: 'total',
                color: '#146eb4'
              }
            ]}
            height={sharedChartHeight}
            slotProps={{
              legend: {
                direction: 'row' as any,
                position: { vertical: 'bottom', horizontal: 'middle' } as any,
              } as any
            }}
            sx={{
              '& .MuiChartsAxis-line': { stroke: '#444' },
              '& .MuiChartsAxis-tick': { stroke: '#444' },
              '& .MuiChartsAxis-tickLabel': { fill: '#000000', fontSize: '11px' },
              '& .MuiChartsLegend-series text': { fill: '#000000 !important', fontSize: '11px' }
            }}
          />
        </div>
      </div>

      {/* Consumer Insights Profiles Section */}
      <div style={{
        backgroundColor: '#d9d6d1',
        padding: '15px 25px 25px 25px',
        borderRadius: '12px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.5)'
      }}>
        <h3 style={{ color: '#000000', textAlign: 'left', marginBottom: '25px', marginTop: '0', fontFamily: 'Satoshi, sans-serif', fontWeight: '900' }}>Consumer Insights</h3>
        <div style={{
          display: 'flex',
          justifyContent: 'space-around',
          alignItems: 'flex-start',
          marginTop: '20px',
          gap: '20px'
        }}>
          {getConsumerProfiles().map((profile) => (
            <div key={profile.personaId} style={{
              textAlign: 'center',
              flex: '1',
              backgroundColor: '#ffffff',
              padding: '15px',
              borderRadius: '8px'
            }}>
              {/* Profile Icon */}
              <div style={{
                width: '100px',
                height: '100px',
                borderRadius: '50%',
                margin: '0 auto 10px',
                overflow: 'hidden',
                border: '2px solid #555'
              }}>
                <img
                  src={personaImages[profile.name]}
                  alt={profile.name}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    transform: 'scale(1.2)'
                  }}
                />
              </div>
              {/* Profile Details */}
              <div style={{
                fontSize: '16px',
                color: '#000000'
              }}>
                <div style={{ fontWeight: '700', color: '#000000', marginBottom: '8px', fontSize: '18px', fontFamily: 'Satoshi, sans-serif' }}>{profile.name}</div>
                {/* Insights */}
                <div style={{
                  textAlign: 'left',
                  marginTop: '10px',
                  fontSize: '14px',
                  lineHeight: '1.5'
                }}>
                  <div style={{ marginBottom: '8px' }}>
                    <strong style={{ color: '#ff9900', fontFamily: 'Satoshi, sans-serif', fontWeight: '700' }}>Likelihood:</strong>
                    <p style={{ margin: '4px 0 0 0', color: '#000000' }}>{profile.insights.likelihood}</p>
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <strong style={{ color: '#146eb4', fontFamily: 'Satoshi, sans-serif', fontWeight: '700' }}>Relevance:</strong>
                    <p style={{ margin: '4px 0 0 0', color: '#000000' }}>{profile.insights.relevance}</p>
                  </div>
                  <div>
                    <strong style={{ color: '#232f3e', fontFamily: 'Satoshi, sans-serif', fontWeight: '700' }}>Intent:</strong>
                    <p style={{ margin: '4px 0 0 0', color: '#000000' }}>{profile.insights.intent}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
      </>
        </div>
      </div>
    </div>
  )
}

export default SearchPage
