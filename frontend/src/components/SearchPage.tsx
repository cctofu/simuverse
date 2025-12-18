import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { PieChart } from '@mui/x-charts/PieChart'
import { BarChart } from '@mui/x-charts/BarChart'
import { Quantum } from 'ldrs/react'
import 'ldrs/react/Quantum.css'
import m1 from '../assets/m1.png'
import m2 from '../assets/m2.png'
import m3 from '../assets/m3.png'
import m4 from '../assets/m4.png'
import f1 from '../assets/f1.png'
import f2 from '../assets/f2.png'
import f3 from '../assets/f3.png'
import f4 from '../assets/f4.png'

// Type definitions
interface Demographics {
  gender?: string
  age?: string
  marital_status?: string
  income?: string
  employment_status?: string
}

interface ClusterProfile {
  tags: string[]
  demographics: Demographics
  pid?: string // Add persona ID
  percentage?: number // Percentage of top_k personas in this cluster
}

interface PersonaFeedback {
  purchase_intent: {
    score: number
    explanation: string
  }
  product_rating: {
    score: number
    explanation: string
  }
  idea_relevance: {
    score: number
    explanation: string
  }
}

interface ApiData {
  gender_distribution: Record<string, number>
  age_distribution: Record<string, number>
  customer_profile: Record<string, ClusterProfile>
}

// API configuration
const API_BASE_URL = 'http://localhost:8000'

// Empty data structure (defined outside component to prevent recreating on every render)
const emptyData: ApiData = {
  gender_distribution: {},
  age_distribution: {},
  customer_profile: {}
}

// Random name arrays
const MALE_NAMES = [
  'James', 'Michael', 'Robert', 'John', 'David', 'William', 'Richard', 'Joseph',
  'Thomas', 'Christopher', 'Daniel', 'Matthew', 'Anthony', 'Mark', 'Donald',
  'Steven', 'Andrew', 'Paul', 'Joshua', 'Kenneth', 'Kevin', 'Brian', 'George',
  'Timothy', 'Ronald', 'Edward', 'Jason', 'Jeffrey', 'Ryan', 'Jacob', 'Gary',
  'Nicholas', 'Eric', 'Jonathan', 'Stephen', 'Larry', 'Justin', 'Scott', 'Brandon',
  'Benjamin', 'Samuel', 'Raymond', 'Gregory', 'Alexander', 'Patrick', 'Frank',
  'Dennis', 'Jerry', 'Tyler', 'Aaron', 'Jose', 'Adam', 'Nathan', 'Henry'
]

const FEMALE_NAMES = [
  'Mary', 'Patricia', 'Jennifer', 'Linda', 'Barbara', 'Elizabeth', 'Susan',
  'Jessica', 'Sarah', 'Karen', 'Lisa', 'Nancy', 'Betty', 'Margaret', 'Sandra',
  'Ashley', 'Kimberly', 'Emily', 'Donna', 'Michelle', 'Carol', 'Amanda', 'Dorothy',
  'Melissa', 'Deborah', 'Stephanie', 'Rebecca', 'Sharon', 'Laura', 'Cynthia',
  'Kathleen', 'Amy', 'Angela', 'Shirley', 'Anna', 'Brenda', 'Pamela', 'Emma',
  'Nicole', 'Helen', 'Samantha', 'Katherine', 'Christine', 'Debra', 'Rachel',
  'Carolyn', 'Janet', 'Catherine', 'Maria', 'Heather', 'Diane', 'Ruth', 'Julie'
]

// Simple seeded random number generator for consistent randomization
const seededRandom = (seed: number): number => {
  const x = Math.sin(seed) * 10000
  return x - Math.floor(x)
}

// Function to get a random name based on gender and pid
const getRandomName = (gender: string | undefined, index: number, pid?: string): string => {
  if (!gender) return `Customer Type ${index + 1}`

  const nameArray = gender.toLowerCase() === 'male' ? MALE_NAMES : FEMALE_NAMES

  // Create a more unique seed using pid if available
  let seed = index * 12345 + 67890
  if (pid) {
    // Extract numeric part from pid (e.g., "user_000009" -> 9)
    const pidMatch = pid.match(/\d+/)
    if (pidMatch) {
      const pidNumber = parseInt(pidMatch[0], 10)
      seed = pidNumber * 7919 + index * 541 // Use prime numbers for better distribution
    }
  }

  const randomValue = seededRandom(seed)
  const nameIndex = Math.floor(randomValue * nameArray.length)
  return nameArray[nameIndex]
}

function SearchPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const productDescription = searchParams.get('product') || ''

  const [data, setData] = useState<ApiData>(emptyData)
  const [loading, setLoading] = useState(false)
  const [chatMode, setChatMode] = useState(false)
  const [selectedCustomer, setSelectedCustomer] = useState<number | null>(null)
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<Array<{ sender: 'user' | 'bot', message: string }>>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [chatLoading, setChatLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [feedbackData, setFeedbackData] = useState<Record<string, PersonaFeedback>>({})

  useEffect(() => {
    const loadData = async () => {
      if (!productDescription) return

      setLoading(true)
      setError(null)

      try {
        const response = await fetch(`${API_BASE_URL}/analyze_product`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ product_description: productDescription })
        })

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`)
        }

        const result = await response.json()
        setData(result)
      } catch (err) {
        console.error('Failed to load data:', err)
        setError('Failed to load product analysis. Please try again.')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [productDescription])

  // Fetch feedback for each persona
  useEffect(() => {
    const fetchFeedback = async () => {
      if (!productDescription || !data.customer_profile || Object.keys(data.customer_profile).length === 0) return

      const profiles = Object.entries(data.customer_profile)

      // Fetch feedback for each persona in parallel
      const feedbackPromises = profiles.map(async ([clusterId, profile]) => {
        const pid = profile.pid || clusterId

        try {
          const response = await fetch(`${API_BASE_URL}/get_persona_feedback`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              pid: pid,
              product_description: productDescription
            })
          })

          if (!response.ok) {
            console.error(`Failed to get feedback for ${pid}`)
            return { pid, feedback: null }
          }

          const result = await response.json()
          return { pid, feedback: result.feedback }
        } catch (err) {
          console.error(`Error fetching feedback for ${pid}:`, err)
          return { pid, feedback: null }
        }
      })

      const results = await Promise.all(feedbackPromises)

      // Build feedback map
      const feedbackMap: Record<string, PersonaFeedback> = {}
      results.forEach(({ pid, feedback }) => {
        if (feedback) {
          feedbackMap[pid] = feedback
        }
      })

      setFeedbackData(feedbackMap)
    }

    fetchFeedback()
  }, [data, productDescription])

  // Transform data for charts
  const getGenderData = () => {
    return Object.entries(data.gender_distribution).map(([name, value]) => ({
      id: name,
      value: value,
      label: `${name}: ${value}`,
      color: name === 'Male' ? '#0080a7' : '#f17269'
    }))
  }

  const getCustomerProfiles = () => {
    return Object.entries(data.customer_profile).map(([clusterId, profile]) => ({
      clusterId,
      tags: profile.tags,
      demographics: profile.demographics,
      pid: profile.pid || clusterId,
      percentage: profile.percentage
    }))
  }

  // Map demographics to profile image
  const getProfileImage = (demographics: Demographics) => {
    if (!demographics.gender || !demographics.age) {
      return m2 // fallback to default
    }

    const gender = demographics.gender.toLowerCase()
    const age = demographics.age

    // Map age ranges to image numbers
    let ageGroup = 1
    if (age === '18-29') ageGroup = 1
    else if (age === '30-49') ageGroup = 2
    else if (age === '50-64') ageGroup = 3
    else if (age === '65+') ageGroup = 4

    // Select image based on gender and age group
    if (gender === 'male') {
      switch (ageGroup) {
        case 1: return m1
        case 2: return m2
        case 3: return m3
        case 4: return m4
        default: return m2
      }
    } else if (gender === 'female') {
      switch (ageGroup) {
        case 1: return f1
        case 2: return f2
        case 3: return f3
        case 4: return f4
        default: return f2
      }
    }

    return m2 // fallback
  }

  // Loading page
  if (loading) {
    return (
      <div style={{
        backgroundColor: '#F8FAFC',
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
        <style>{`
          @font-face {
            font-family: 'Comfortaa';
            src: url('/src/assets/fonts/Comfortaa-Light.ttf') format('truetype');
            font-weight: 300;
            font-style: normal;
          }

          @font-face {
            font-family: 'Comfortaa';
            src: url('/src/assets/fonts/Comfortaa-Regular.ttf') format('truetype');
            font-weight: 400;
            font-style: normal;
          }

          @font-face {
            font-family: 'Comfortaa';
            src: url('/src/assets/fonts/Comfortaa-Bold.ttf') format('truetype');
            font-weight: 700;
            font-style: normal;
          }

          @keyframes float1 {
            0%, 100% {
              transform: translate(0, 0) scale(1);
              opacity: 0.6;
            }
            50% {
              transform: translate(30px, -30px) scale(1.1);
              opacity: 0.8;
            }
          }

          @keyframes float2 {
            0%, 100% {
              transform: translate(0, 0) scale(1);
              opacity: 0.5;
            }
            50% {
              transform: translate(-40px, 40px) scale(1.15);
              opacity: 0.7;
            }
          }

          @keyframes float3 {
            0%, 100% {
              transform: translate(0, 0) scale(1);
              opacity: 0.4;
            }
            50% {
              transform: translate(20px, 50px) scale(1.2);
              opacity: 0.6;
            }
          }

          .aurora-orb-1 {
            position: absolute;
            width: 800px;
            height: 800px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(167, 139, 250, 0.65) 0%, rgba(167, 139, 250, 0) 70%);
            filter: blur(60px);
            top: -200px;
            right: -100px;
            animation: float1 20s ease-in-out infinite;
            pointer-events: none;
          }

          .aurora-orb-2 {
            position: absolute;
            width: 700px;
            height: 700px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(147, 197, 253, 0.6) 0%, rgba(147, 197, 253, 0) 70%);
            filter: blur(70px);
            bottom: -150px;
            left: -150px;
            animation: float2 25s ease-in-out infinite;
            pointer-events: none;
          }

          .aurora-orb-3 {
            position: absolute;
            width: 650px;
            height: 650px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(232, 121, 249, 0.55) 0%, rgba(232, 121, 249, 0) 70%);
            filter: blur(80px);
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            animation: float3 30s ease-in-out infinite;
            pointer-events: none;
          }

          @keyframes fadeInOut {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
          }
        `}</style>

        {/* Aurora gradient orbs */}
        <div className="aurora-orb-1"></div>
        <div className="aurora-orb-2"></div>
        <div className="aurora-orb-3"></div>

        <div style={{
          width: '600px',
          maxWidth: '90%',
          backgroundColor: 'rgba(255, 255, 255, 0.7)',
          backdropFilter: 'blur(40px)',
          WebkitBackdropFilter: 'blur(40px)',
          padding: '50px 40px',
          borderRadius: '24px',
          boxShadow: '0 20px 60px rgba(139, 92, 246, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.8)',
          border: '1px solid rgba(255, 255, 255, 0.9)',
          textAlign: 'center',
          fontFamily: 'Comfortaa, sans-serif',
          position: 'relative',
          zIndex: 1
        }}>
          {/* Loading */}
          <div>
            <Quantum
            size="55"
            speed="1.75"
            color="black"
          />
          </div>

          <h2 style={{
            color: '#1E1B4B',
            fontSize: '28px',
            fontWeight: '700',
            marginBottom: '12px',
            fontFamily: 'Comfortaa, sans-serif'
          }}>
            Analyzing Product
          </h2>

          <p style={{
            color: '#475569',
            fontSize: '16px',
            fontWeight: '400',
            marginBottom: '25px',
            fontFamily: 'Comfortaa, sans-serif',
            animation: 'fadeInOut 3s ease-in-out infinite'
          }}>
            Clustering the personas...
          </p>

          <p style={{
            color: '#1E1B4B',
            fontSize: '18px',
            fontWeight: '700',
            padding: '15px 20px',
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            borderRadius: '12px',
            marginBottom: '20px',
            border: '1px solid rgba(139, 92, 246, 0.2)'
          }}>
            {productDescription}
          </p>

          <button
            onClick={() => window.location.href = '/'}
            style={{
              background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 50%, #6D28D9 100%)',
              color: '#FFFFFF',
              padding: '12px 28px',
              borderRadius: '10px',
              fontSize: '15px',
              fontWeight: '700',
              fontFamily: 'Comfortaa, sans-serif',
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              marginTop: '10px',
              boxShadow: '0 4px 12px rgba(139, 92, 246, 0.3)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 6px 16px rgba(139, 92, 246, 0.4)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(139, 92, 246, 0.3)'
            }}
          >
            Cancel Generation
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={{
      backgroundColor: '#FFFFFF',
      height: '100vh',
      width: '100vw',
      overflow: 'hidden',
      position: 'fixed',
      top: 0,
      left: 0
    }}>
      <style>{`
        @font-face {
          font-family: 'Comfortaa';
          src: url('/src/assets/fonts/Comfortaa-Light.ttf') format('truetype');
          font-weight: 300;
          font-style: normal;
        }

        @font-face {
          font-family: 'Comfortaa';
          src: url('/src/assets/fonts/Comfortaa-Regular.ttf') format('truetype');
          font-weight: 400;
          font-style: normal;
        }

        @font-face {
          font-family: 'Comfortaa';
          src: url('/src/assets/fonts/Comfortaa-Bold.ttf') format('truetype');
          font-weight: 700;
          font-style: normal;
        }
      `}</style>
      {/* Header Tab Bar */}
      <div style={{
        backgroundColor: '#FFFFFF',
        borderBottom: '1px solid #E5E0F3',
        padding: '20px 3vw',
        display: 'flex',
        alignItems: 'center',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
        position: 'sticky',
        top: 0,
        zIndex: 100
      }}>
        <h1 style={{
          color: '#9860d7ff',
          fontSize: '32px',
          fontWeight: '700',
          letterSpacing: '2px',
          margin: 0,
          fontFamily: 'Akira, sans-serif'
        }}>
          Simuverse
        </h1>
      </div>

      <div style={{
        height: 'calc(100vh - 72px)',
        overflowY: 'auto',
        padding: '2vh 3vw',
        fontFamily: 'Comfortaa, sans-serif',
        width: '100%',
        boxSizing: 'border-box'
      }}>
          {/* Product Box */}
          <div style={{
            backgroundColor: '#F7F7F9',
            padding: '12px 20px',
            borderRadius: '10px',
            marginBottom: '2vh',
            border: '1px solid #E5E0F3',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '20px'
          }}>
            <div style={{
              flex: 1,
              display: 'flex',
              alignItems: 'baseline',
              gap: '12px'
            }}>
              <span style={{
                fontSize: '12px',
                fontWeight: '700',
                color: '#6C5A87',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Product:
              </span>
              <span style={{
                fontSize: '16px',
                fontWeight: '700',
                color: '#7D2ADD',
                fontFamily: 'Comfortaa, sans-serif'
              }}>
                {productDescription}
              </span>
            </div>
            <button
              onClick={() => navigate(`/?product=${encodeURIComponent(productDescription)}`)}
              style={{
                backgroundColor: '#7D2ADD',
                color: '#FFFFFF',
                padding: '8px 20px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: '700',
                fontFamily: 'Comfortaa, sans-serif',
                border: 'none',
                cursor: 'pointer',
                transition: 'background-color 0.2s',
                whiteSpace: 'nowrap'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#9258d4ff'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#7D2ADD'
              }}
            >
              Change Product
            </button>
          </div>

          {/* Error Banner */}
          {error && (
            <div style={{
              backgroundColor: '#FEE',
              border: '1px solid #FCC',
              borderRadius: '8px',
              padding: '12px 20px',
              marginBottom: '20px',
              color: '#C33',
              fontFamily: 'Comfortaa, sans-serif'
            }}>
              {error}
            </div>
          )}

          {/* Content - 4 Column Layout */}
          <>
      <div style={{
        display: 'grid',
        gridTemplateColumns: chatMode ? '0.9fr 2.95fr' : '0.9fr 0.9fr 0.9fr 1.05fr',
        gap: '1.5vw',
        transition: 'grid-template-columns 0.6s ease-in-out'
      }}>
        {/* Customer Type Boxes - First 3 Columns */}
        {!chatMode && getCustomerProfiles().map((profile, index) => {
          // Helper function to get subtitle based on demographics
          const getSubtitle = (demographics: Demographics) => {
            const age = demographics.age || ''
            const employment = demographics.employment_status || ''
            const marital = demographics.marital_status || ''

            if (employment.toLowerCase().includes('retired')) {
              return 'Retired Professional'
            } else if (employment.toLowerCase().includes('employed') && age === '18-29') {
              return 'Young Professional'
            } else if (employment.toLowerCase().includes('employed') && marital.toLowerCase().includes('married')) {
              return 'Working Parent'
            } else if (employment.toLowerCase().includes('employed')) {
              return 'Working Professional'
            }
            return 'Community Member'
          }

          // Helper function to assign random colors to traits
          const traitColors = [
            { bg: '#DBEAFE', color: '#1E40AF' }, // Blue
            { bg: '#D1FAE5', color: '#065F46' }, // Green
            { bg: '#FEE2E2', color: '#991B1B' }, // Red
            { bg: '#FEF3C7', color: '#92400E' }, // Yellow
            { bg: '#E9D5FF', color: '#6B21A8' }, // Purple
            { bg: '#FCE7F3', color: '#9F1239' }, // Pink
            { bg: '#FFEDD5', color: '#9A3412' }, // Orange
            { bg: '#F0FDF4', color: '#166534' }  // Emerald
          ]

          const getTraitColor = (index: number) => {
            return traitColors[index % traitColors.length]
          }

          // Limit tags to 5
          const limitedTags = profile.tags.slice(0, 5)

          return (
            <div key={profile.clusterId} style={{
              backgroundColor: '#F7F7F9',
              padding: '1vh 1vw 1.5vh 1vw',
              borderRadius: '10px',
              boxShadow: '0 2px 8px rgba(125, 42, 221, 0.1)',
              border: '1px solid #E5E0F3',
              minHeight: '60vh',
              display: 'flex',
              flexDirection: 'column',
              position: 'relative'
            }}>
              <div style={{ flex: 1 }}>
                {/* Name and Match Badge Row */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '10px'
                }}>
                  <div>
                    {/* Name */}
                    <h3 style={{
                      color: '#2B2140',
                      margin: '0 0 4px 0',
                      fontFamily: 'Comfortaa, sans-serif',
                      fontWeight: '700',
                      fontSize: '16px'
                    }}>
                      {getRandomName(profile.demographics.gender, index, profile.pid)}
                    </h3>
                    {/* Subtitle under name */}
                    <p style={{
                      color: '#6C5A87',
                      fontSize: '11px',
                      fontWeight: '400',
                      margin: '0',
                      fontFamily: 'Comfortaa, sans-serif'
                    }}>
                      {getSubtitle(profile.demographics)}
                    </p>
                  </div>
                  {/* Match Badge on the right */}
                  {profile.percentage !== undefined && (
                    <span style={{
                      backgroundColor: '#c3a0ebff',
                      color: '#FFFFFF',
                      padding: '3px 8px',
                      borderRadius: '12px',
                      fontSize: '10px',
                      fontWeight: '700',
                      fontFamily: 'Comfortaa, sans-serif',
                      whiteSpace: 'nowrap'
                    }}>
                      {profile.percentage}% of Population
                    </span>
                  )}
                </div>

                <img
                  src={getProfileImage(profile.demographics)}
                  alt="Customer Profile"
                  style={{
                    width: '100px',
                    height: '120px',
                    objectFit: 'cover',
                    marginBottom: '10px'
                  }}
                />

                {/* Demographics - Two Column Table */}
                {profile.demographics && Object.keys(profile.demographics).length > 0 && (
                  <div
                    style={{
                      backgroundColor: '#FFFFFF',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid #E5E0F3',
                      marginBottom: '12px'
                    }}
                  >
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'auto 1fr',
                      gap: '6px 10px',
                      fontFamily: 'Comfortaa, sans-serif'
                    }}>
                      {Object.entries(profile.demographics).map(([key, value]) => (
                        <>
                          <div
                            key={`${key}-label`}
                            style={{
                              fontWeight: 700,
                              fontSize: '10px',
                              color: '#6C5A87',
                              textAlign: 'right'
                            }}
                          >
                            {key === 'employment_status' ? 'Employment' : key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </div>
                          <div
                            key={`${key}-value`}
                            style={{
                              fontSize: '10px',
                              color: '#2B2140',
                              fontWeight: 500
                            }}
                          >
                            {value}
                          </div>
                        </>
                      ))}
                    </div>
                  </div>
                )}

                {/* KEY TRAITS Header */}
                <div style={{
                  fontSize: '10px',
                  fontWeight: '700',
                  color: '#6C5A87',
                  marginBottom: '6px',
                  letterSpacing: '0.5px',
                  fontFamily: 'Comfortaa, sans-serif'
                }}>
                  KEY TRAITS
                </div>

                {/* Multi-colored Trait Chips */}
                <div style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '5px',
                  justifyContent: 'flex-start',
                  marginBottom: '12px'
                }}>
                  {limitedTags.map((tag, tagIndex) => {
                    const colors = getTraitColor(tagIndex)
                    return (
                      <span key={tagIndex} style={{
                        backgroundColor: colors.bg,
                        color: colors.color,
                        padding: '4px 8px',
                        borderRadius: '12px',
                        fontSize: '10px',
                        fontWeight: '700',
                        fontFamily: 'Comfortaa, sans-serif',
                        display: 'inline-block'
                      }}>
                        {tag}
                      </span>
                    )
                  })}
                </div>

                {/* FEEDBACK Section */}
                <div style={{
                  fontSize: '10px',
                  fontWeight: '700',
                  color: '#6C5A87',
                  marginBottom: '6px',
                  marginTop: '12px',
                  letterSpacing: '0.5px',
                  fontFamily: 'Comfortaa, sans-serif'
                }}>
                  FEEDBACK
                </div>

                <div style={{
                  backgroundColor: '#FFFFFF',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: '1px solid #E5E0F3',
                  marginBottom: '12px'
                }}>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'auto 1fr',
                    gap: '6px 10px',
                    fontFamily: 'Comfortaa, sans-serif'
                  }}>
                    <div style={{
                      fontWeight: 700,
                      fontSize: '10px',
                      color: '#6C5A87',
                      textAlign: 'right'
                    }}>
                      Purchase Intent?
                    </div>
                    <div style={{
                      fontSize: '10px',
                      color: '#2B2140',
                      fontWeight: 500
                    }}>
                      {feedbackData[profile.pid]?.purchase_intent.score || '—'}
                    </div>

                    <div style={{
                      fontWeight: 700,
                      fontSize: '10px',
                      color: '#6C5A87',
                      textAlign: 'right'
                    }}>
                      Product Rating
                    </div>
                    <div style={{
                      fontSize: '10px',
                      color: '#2B2140',
                      fontWeight: 500
                    }}>
                      {feedbackData[profile.pid]?.product_rating.score || '—'}
                    </div>

                    <div style={{
                      fontWeight: 700,
                      fontSize: '10px',
                      color: '#6C5A87',
                      textAlign: 'right'
                    }}>
                      Idea Relevance
                    </div>
                    <div style={{
                      fontSize: '10px',
                      color: '#2B2140',
                      fontWeight: 500
                    }}>
                      {feedbackData[profile.pid]?.idea_relevance.score || '—'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Ask [Name] Button - Purple Pill with Icon */}
              <button style={{
                backgroundColor: '#7D2ADD',
                color: '#FFFFFF',
                padding: '8px 14px',
                borderRadius: '16px',
                fontSize: '11px',
                fontWeight: '700',
                fontFamily: 'Comfortaa, sans-serif',
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                alignSelf: 'flex-start'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#9258d4ff'
                e.currentTarget.style.transform = 'translateY(-1px)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#7D2ADD'
                e.currentTarget.style.transform = 'translateY(0)'
              }}
              onClick={() => {
                setSelectedCustomer(index)
                setTimeout(() => {
                  setChatMode(true)
                }, 600)
              }}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                Ask {getRandomName(profile.demographics.gender, index, profile.pid)}
              </button>
            </div>
          )
        })}

        {/* Chat Mode Layout */}
        {chatMode && selectedCustomer !== null && (() => {
          const profile = getCustomerProfiles()[selectedCustomer]

          // Helper function to get subtitle based on demographics
          const getSubtitle = (demographics: Demographics) => {
            const age = demographics.age || ''
            const employment = demographics.employment_status || ''
            const marital = demographics.marital_status || ''

            if (employment.toLowerCase().includes('retired')) {
              return 'Retired Professional'
            } else if (employment.toLowerCase().includes('employed') && age === '18-29') {
              return 'Young Professional'
            } else if (employment.toLowerCase().includes('employed') && marital.toLowerCase().includes('married')) {
              return 'Working Parent'
            } else if (employment.toLowerCase().includes('employed')) {
              return 'Working Professional'
            }
            return 'Community Member'
          }

          // Helper function to assign random colors to traits
          const traitColors = [
            { bg: '#DBEAFE', color: '#1E40AF' }, // Blue
            { bg: '#D1FAE5', color: '#065F46' }, // Green
            { bg: '#FEE2E2', color: '#991B1B' }, // Red
            { bg: '#FEF3C7', color: '#92400E' }, // Yellow
            { bg: '#E9D5FF', color: '#6B21A8' }, // Purple
            { bg: '#FCE7F3', color: '#9F1239' }, // Pink
            { bg: '#FFEDD5', color: '#9A3412' }, // Orange
            { bg: '#F0FDF4', color: '#166534' }  // Emerald
          ]

          const getTraitColor = (index: number) => {
            return traitColors[index % traitColors.length]
          }

          // Limit tags to 5
          const limitedTags = profile.tags.slice(0, 5)

          return (
            <>
              {/* Selected Customer Card - Column 1 */}
              <div style={{
                backgroundColor: '#F7F7F9',
                padding: '1vh 1vw 1.5vh 1vw',
                borderRadius: '10px',
                boxShadow: '0 2px 8px rgba(125, 42, 221, 0.1)',
                border: '1px solid #E5E0F3',
                minHeight: '60vh',
                animation: 'slideIn 0.6s ease-in-out',
                position: 'relative'
              }}>
                {/* Name and Match Badge Row */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '4px'
                }}>
                  <div>
                    {/* Name */}
                    <h3 style={{
                      color: '#2B2140',
                      margin: '0 0 4px 0',
                      fontFamily: 'Comfortaa, sans-serif',
                      fontWeight: '700',
                      fontSize: '16px'
                    }}>
                      {getRandomName(profile.demographics.gender, selectedCustomer, profile.pid)}
                    </h3>
                    {/* Subtitle under name */}
                    <p style={{
                      color: '#6C5A87',
                      fontSize: '11px',
                      fontWeight: '400',
                      margin: '0',
                      fontFamily: 'Comfortaa, sans-serif'
                    }}>
                      {getSubtitle(profile.demographics)}
                    </p>
                  </div>
                  {/* Match Badge on the right */}
                  {profile.percentage !== undefined && (
                    <span style={{
                      backgroundColor: '#7D2ADD',
                      color: '#FFFFFF',
                      padding: '3px 8px',
                      borderRadius: '12px',
                      fontSize: '10px',
                      fontWeight: '700',
                      fontFamily: 'Comfortaa, sans-serif',
                      whiteSpace: 'nowrap'
                    }}>
                      {profile.percentage}% Match
                    </span>
                  )}
                </div>

                <img
                  src={getProfileImage(profile.demographics)}
                  alt="Customer Profile"
                  style={{
                    width: '100px',
                    height: '120px',
                    objectFit: 'cover',
                    marginBottom: '10px'
                  }}
                />

                {/* Demographics - Two Column Table */}
                {profile.demographics && Object.keys(profile.demographics).length > 0 && (
                  <div
                    style={{
                      backgroundColor: '#FFFFFF',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid #E5E0F3',
                      marginBottom: '12px'
                    }}
                  >
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'auto 1fr',
                      gap: '6px 10px',
                      fontFamily: 'Comfortaa, sans-serif'
                    }}>
                      {Object.entries(profile.demographics).map(([key, value]) => (
                        <>
                          <div
                            key={`${key}-label`}
                            style={{
                              fontWeight: 700,
                              fontSize: '10px',
                              color: '#6C5A87',
                              textAlign: 'right'
                            }}
                          >
                            {key === 'employment_status' ? 'Employment' : key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </div>
                          <div
                            key={`${key}-value`}
                            style={{
                              fontSize: '10px',
                              color: '#2B2140',
                              fontWeight: 500
                            }}
                          >
                            {value}
                          </div>
                        </>
                      ))}
                    </div>
                  </div>
                )}

                {/* KEY TRAITS Header */}
                <div style={{
                  fontSize: '10px',
                  fontWeight: '700',
                  color: '#6C5A87',
                  marginBottom: '6px',
                  letterSpacing: '0.5px',
                  fontFamily: 'Comfortaa, sans-serif'
                }}>
                  KEY TRAITS
                </div>

                {/* Multi-colored Trait Chips */}
                <div style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '5px',
                  justifyContent: 'flex-start',
                  marginBottom: '12px'
                }}>
                  {limitedTags.map((tag, tagIndex) => {
                    const colors = getTraitColor(tagIndex)
                    return (
                      <span key={tagIndex} style={{
                        backgroundColor: colors.bg,
                        color: colors.color,
                        padding: '4px 8px',
                        borderRadius: '12px',
                        fontSize: '10px',
                        fontWeight: '700',
                        fontFamily: 'Comfortaa, sans-serif',
                        display: 'inline-block'
                      }}>
                        {tag}
                      </span>
                    )
                  })}
                </div>

                {/* FEEDBACK Section */}
                <div style={{
                  fontSize: '10px',
                  fontWeight: '700',
                  color: '#6C5A87',
                  marginBottom: '6px',
                  marginTop: '12px',
                  letterSpacing: '0.5px',
                  fontFamily: 'Comfortaa, sans-serif'
                }}>
                  FEEDBACK
                </div>

                <div style={{
                  backgroundColor: '#FFFFFF',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: '1px solid #E5E0F3',
                  marginBottom: '12px'
                }}>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'auto 1fr',
                    gap: '6px 10px',
                    fontFamily: 'Comfortaa, sans-serif'
                  }}>
                    <div style={{
                      fontWeight: 700,
                      fontSize: '10px',
                      color: '#6C5A87',
                      textAlign: 'right'
                    }}>
                      Purchase Intent?
                    </div>
                    <div style={{
                      fontSize: '10px',
                      color: '#2B2140',
                      fontWeight: 500
                    }}>
                      {feedbackData[profile.pid]?.purchase_intent.score || '—'}
                    </div>

                    <div style={{
                      fontWeight: 700,
                      fontSize: '10px',
                      color: '#6C5A87',
                      textAlign: 'right'
                    }}>
                      Product Rating
                    </div>
                    <div style={{
                      fontSize: '10px',
                      color: '#2B2140',
                      fontWeight: 500
                    }}>
                      {feedbackData[profile.pid]?.product_rating.score || '—'}
                    </div>

                    <div style={{
                      fontWeight: 700,
                      fontSize: '10px',
                      color: '#6C5A87',
                      textAlign: 'right'
                    }}>
                      Idea Relevance
                    </div>
                    <div style={{
                      fontSize: '10px',
                      color: '#2B2140',
                      fontWeight: 500
                    }}>
                      {feedbackData[profile.pid]?.idea_relevance.score || '—'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Chat Box - Columns 2, 3 & 4 */}
              <div style={{
                backgroundColor: '#F7F7F9',
                padding: '1.5vh 1.5vw 2vh 1.5vw',
                borderRadius: '12px',
                boxShadow: '0 2px 8px rgba(125, 42, 221, 0.1)',
                border: '1px solid #E5E0F3',
                minHeight: '60vh',
                display: 'flex',
                flexDirection: 'column',
                animation: 'fadeIn 0.6s ease-in-out'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                  <h3 style={{
                    color: '#2B2140',
                    textAlign: 'left',
                    marginBottom: '0',
                    marginTop: '0',
                    fontFamily: 'Comfortaa, sans-serif',
                    fontWeight: '700',
                    fontSize: '20px'
                  }}>
                    Chat with {getRandomName(profile.demographics.gender, selectedCustomer, profile.pid)}
                  </h3>
                  <button
                    onClick={() => {
                      setChatMode(false)
                      setSelectedCustomer(null)
                      setChatHistory([])
                      setSessionId(null)
                    }}
                    style={{
                      backgroundColor: '#d2d3ff',
                      color: '#2B2140',
                      padding: '8px 16px',
                      borderRadius: '8px',
                      fontSize: '14px',
                      fontWeight: '700',
                      fontFamily: 'Comfortaa, sans-serif',
                      border: 'none',
                      cursor: 'pointer',
                      transition: 'background-color 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = '#b8b9f5'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = '#d2d3ff'
                    }}
                  >
                    Close Chat
                  </button>
                </div>

                {/* Chat History */}
                <div style={{
                  flex: 1,
                  overflowY: 'auto',
                  marginBottom: '15px',
                  padding: '15px',
                  backgroundColor: '#FFFFFF',
                  borderRadius: '8px',
                  border: '1px solid #E5E0F3'
                }}>
                  {chatHistory.length === 0 ? (
                    <p style={{
                      color: '#6C5A87',
                      fontFamily: 'Comfortaa, sans-serif',
                      textAlign: 'center',
                      marginTop: '20px'
                    }}>
                      Start a conversation by typing a message below
                    </p>
                  ) : (
                    chatHistory.map((msg, idx) => (
                      <div
                        key={idx}
                        style={{
                          marginBottom: '10px',
                          padding: '10px 15px',
                          borderRadius: '8px',
                          backgroundColor: msg.sender === 'user' ? '#E9D9FB' : '#e5f1f2',
                          color: msg.sender === 'user' ? '#7D2ADD' : '#2B2140',
                          fontFamily: 'Comfortaa, sans-serif',
                          textAlign: msg.sender === 'user' ? 'right' : 'left',
                          marginLeft: msg.sender === 'user' ? 'auto' : '0',
                          marginRight: msg.sender === 'user' ? '0' : 'auto',
                          maxWidth: '80%',
                          width: 'fit-content'
                        }}
                      >
                        {msg.message}
                      </div>
                    ))
                  )}
                  {chatLoading && (
                    <div style={{
                      padding: '10px 15px',
                      borderRadius: '8px',
                      backgroundColor: '#e5f1f2',
                      color: '#6C5A87',
                      fontFamily: 'Comfortaa, sans-serif',
                      fontStyle: 'italic',
                      maxWidth: '80%'
                    }}>
                      Typing...
                    </div>
                  )}
                </div>

                {/* Chat Input */}
                <div style={{ display: 'flex', gap: '10px' }}>
                  <input
                    type="text"
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    onKeyDown={async (e) => {
                      if (e.key === 'Enter' && chatMessage.trim() && !chatLoading) {
                        const userMessage = chatMessage
                        setChatMessage('')
                        setChatHistory([...chatHistory, { sender: 'user', message: userMessage }])
                        setChatLoading(true)

                        try {
                          const currentProfile = getCustomerProfiles()[selectedCustomer]
                          const response = await fetch(`${API_BASE_URL}/ask_persona`, {
                            method: 'POST',
                            headers: {
                              'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                              pid: currentProfile?.pid || 'user_000009',
                              question: userMessage,
                              session_id: sessionId
                            })
                          })

                          if (!response.ok) {
                            throw new Error(`API error: ${response.status}`)
                          }

                          const result = await response.json()

                          // Store session ID for future messages
                          if (!sessionId && result.session_id) {
                            setSessionId(result.session_id)
                          }

                          setChatHistory(prev => [...prev, {
                            sender: 'bot',
                            message: result.response
                          }])
                        } catch (err) {
                          console.error('Chat error:', err)
                          setChatHistory(prev => [...prev, {
                            sender: 'bot',
                            message: 'Sorry, I encountered an error. Please try again.'
                          }])
                        } finally {
                          setChatLoading(false)
                        }
                      }
                    }}
                    placeholder="Type your question..."
                    disabled={chatLoading}
                    style={{
                      flex: 1,
                      padding: '12px 16px',
                      borderRadius: '8px',
                      border: '1px solid #E5E0F3',
                      fontSize: '16px',
                      fontFamily: 'Comfortaa, sans-serif',
                      outline: 'none',
                      opacity: chatLoading ? 0.6 : 1
                    }}
                  />
                  <button
                    onClick={async () => {
                      if (chatMessage.trim() && !chatLoading) {
                        const userMessage = chatMessage
                        setChatMessage('')
                        setChatHistory([...chatHistory, { sender: 'user', message: userMessage }])
                        setChatLoading(true)

                        try {
                          const currentProfile = getCustomerProfiles()[selectedCustomer]
                          const response = await fetch(`${API_BASE_URL}/ask_persona`, {
                            method: 'POST',
                            headers: {
                              'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                              pid: currentProfile?.pid || 'user_000009',
                              question: userMessage,
                              session_id: sessionId
                            })
                          })

                          if (!response.ok) {
                            throw new Error(`API error: ${response.status}`)
                          }

                          const result = await response.json()

                          // Store session ID for future messages
                          if (!sessionId && result.session_id) {
                            setSessionId(result.session_id)
                          }

                          setChatHistory(prev => [...prev, {
                            sender: 'bot',
                            message: result.response
                          }])
                        } catch (err) {
                          console.error('Chat error:', err)
                          setChatHistory(prev => [...prev, {
                            sender: 'bot',
                            message: 'Sorry, I encountered an error. Please try again.'
                          }])
                        } finally {
                          setChatLoading(false)
                        }
                      }
                    }}
                    disabled={chatLoading}
                    style={{
                      backgroundColor: '#7D2ADD',
                      color: '#FFFFFF',
                      padding: '12px 24px',
                      borderRadius: '8px',
                      fontSize: '16px',
                      fontWeight: '700',
                      fontFamily: 'Comfortaa, sans-serif',
                      border: 'none',
                      cursor: chatLoading ? 'not-allowed' : 'pointer',
                      opacity: chatLoading ? 0.6 : 1
                    }}
                  >
                    {chatLoading ? 'Sending...' : 'Send'}
                  </button>
                </div>
              </div>
            </>
          )
        })()}

        {/* Charts Column - 4th Column with Stacked Charts */}
        {!chatMode && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1.5vw'
        }}>
          {/* Gender Distribution Pie Chart */}
          <div style={{
            backgroundColor: '#F7F7F9',
            padding: '1.5vh 1.5vw 2vh 1.5vw',
            borderRadius: '12px',
            boxShadow: '0 2px 8px rgba(125, 42, 221, 0.1)',
            border: '1px solid #E5E0F3'
          }}>
            <h3 style={{ textAlign: 'left', marginBottom: '15px', color: '#2B2140', marginTop: '0', fontFamily: 'Comfortaa, sans-serif', fontWeight: '700' }}>Gender Distribution</h3>
            <PieChart
              series={[
                {
                  data: getGenderData(),
                  highlightScope: { fade: 'global', highlight: 'item' },
                },
              ]}
              height={180}
              slotProps={{
                legend: {
                  direction: 'row' as any,
                  position: { vertical: 'bottom', horizontal: 'middle' } as any,
                } as any
              }}
              sx={{
                '& .MuiPieArc-root': { stroke: '#F7F7F9', strokeWidth: 2 },
                '& text': { fill: '#2B2140 !important', fontWeight: 600 },
                '& .MuiChartsLegend-series text': { fill: '#2B2140 !important' }
              }}
            />
          </div>

          {/* Age Distribution Bar Chart */}
          <div style={{
            backgroundColor: '#F7F7F9',
            borderRadius: '12px',
            boxShadow: '0 2px 8px rgba(125, 42, 221, 0.1)',
            border: '1px solid #E5E0F3',
            flex: '1',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <h3 style={{ textAlign: 'left', marginBottom: '0', color: '#2B2140', marginTop: '0', fontFamily: 'Comfortaa, sans-serif', fontWeight: '700', padding: '1.5vh 1.5vw 0 1.5vw' }}>Age Distribution</h3>
            <div style={{ flex: 1, display: 'flex', alignItems: 'center' }}>
              <BarChart
                xAxis={[{
                  scaleType: 'band',
                  data: ['18-29', '30-49', '50-64', '65+']
                }]}
                series={[
                  {
                    data: [
                      data.age_distribution['18-29'] || 0,
                      data.age_distribution['30-49'] || 0,
                      data.age_distribution['50-64'] || 0,
                      data.age_distribution['65+'] || 0
                    ],
                    barLabel: 'value'
                  }
                ]}
                height={400}
                sx={{
                  '& .MuiChartsAxis-line': { stroke: '#6C5A87' },
                  '& .MuiChartsAxis-tick': { stroke: '#6C5A87' },
                  '& .MuiChartsAxis-tickLabel': { fill: '#2B2140', fontSize: '12px' },
                  '& .MuiBarElement-root:nth-of-type(1)': { fill: '#f17269' },
                  '& .MuiBarElement-root:nth-of-type(2)': { fill: '#0080a7' },
                  '& .MuiBarElement-root:nth-of-type(3)': { fill: '#fedab6' },
                  '& .MuiBarElement-root:nth-of-type(4)': { fill: '#6AA88E' },
                  '& .MuiChartsLegend-root': { display: 'none' }
                }}
              />
            </div>
          </div>
        </div>
        )}
      </div>
      </>
      </div>
    </div>
  )
}

export default SearchPage
