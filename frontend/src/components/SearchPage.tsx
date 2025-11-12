import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
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

// Function to get a random name based on gender
const getRandomName = (gender: string | undefined, index: number): string => {
  if (!gender) return `Customer Type ${index + 1}`

  const nameArray = gender.toLowerCase() === 'male' ? MALE_NAMES : FEMALE_NAMES
  // Use seeded random to pick a name based on index
  const seed = index * 12345 + 67890 // Add constants to make it more random
  const randomValue = seededRandom(seed)
  const nameIndex = Math.floor(randomValue * nameArray.length)
  return nameArray[nameIndex]
}

function SearchPage() {
  const [searchParams] = useSearchParams()
  const productDescription = searchParams.get('product') || ''

  const [data, setData] = useState<ApiData>(emptyData)
  const [loading, setLoading] = useState(false)
  const [chatMode, setChatMode] = useState(false)
  const [selectedCustomer, setSelectedCustomer] = useState<number | null>(null)
  const [chatMessage, setChatMessage] = useState('')
  const [chatHistory, setChatHistory] = useState<Array<{ sender: 'user' | 'bot', message: string }>>([])
  const [isAnimating, setIsAnimating] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [chatLoading, setChatLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
        backgroundColor: '#FFFFFF',
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
        <div style={{
          width: '600px',
          backgroundColor: '#F7F7F9',
          padding: '40px',
          borderRadius: '16px',
          boxShadow: '0 8px 24px rgba(125, 42, 221, 0.15)',
          border: '1px solid #E5E0F3',
          textAlign: 'center'
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
            color: '#2B2140',
            fontSize: '24px',
            fontWeight: '600',
            marginBottom: '15px'
          }}>
            Analyzing Product...
          </h2>
          <p style={{
            color: '#7D2ADD',
            fontSize: '18px',
            fontWeight: '600',
            padding: '15px',
            backgroundColor: '#E9D9FB',
            borderRadius: '8px'
          }}>
            {productDescription}
          </p>
        </div>

        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          @keyframes slideIn {
            0% {
              opacity: 0;
              transform: translateX(50%);
            }
            100% {
              opacity: 1;
              transform: translateX(0);
            }
          }
          @keyframes fadeIn {
            0% {
              opacity: 0;
              transform: scale(0.95);
            }
            100% {
              opacity: 1;
              transform: scale(1);
            }
          }
        `}</style>
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
      <div style={{
        height: '100vh',
        overflowY: 'auto',
        padding: '2vh 3vw',
        fontFamily: 'Satoshi, sans-serif',
        width: '100%',
        boxSizing: 'border-box'
      }}>
          {/* Header with Logo and Product */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            marginBottom: '3vh',
            gap: '20px'
          }}>
            <h1 style={{
              color: '#7D2ADD',
              fontSize: '36px',
              fontWeight: '700',
              letterSpacing: '2px',
              margin: 0,
              fontFamily: 'Akira, sans-serif'
            }}>
              Simuverse
            </h1>
            <div>
              <strong style={{ color: '#2B2140' }}>Product:</strong>
              <span style={{ fontSize: '22px', fontWeight: '900', color: '#7D2ADD', marginLeft: '8px', fontFamily: 'Satoshi, sans-serif' }}>
                {productDescription}
              </span>
            </div>
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
              fontFamily: 'Satoshi, sans-serif'
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
        {!chatMode && getCustomerProfiles().map((profile, index) => (
          <div key={profile.clusterId} style={{
            backgroundColor: '#F7F7F9',
            padding: '1.5vh 1.5vw 2vh 1.5vw',
            borderRadius: '12px',
            boxShadow: '0 2px 8px rgba(125, 42, 221, 0.1)',
            border: '1px solid #E5E0F3',
            minHeight: '75vh',
            display: 'flex',
            flexDirection: 'column',
            position: 'relative'
          }}>
            {/* Percentage Badge in Top Right */}
            {profile.percentage !== undefined && (
              <div style={{
                position: 'absolute',
                top: '12px',
                right: '12px',
                backgroundColor: '#7D2ADD',
                color: '#FFFFFF',
                padding: '6px 12px',
                borderRadius: '20px',
                fontSize: '14px',
                fontWeight: '700',
                fontFamily: 'Satoshi, sans-serif',
                boxShadow: '0 2px 6px rgba(125, 42, 221, 0.3)'
              }}>
                {profile.percentage}%
              </div>
            )}
            <div style={{ flex: 1 }}>
              <h3 style={{
                color: '#2B2140',
                textAlign: 'left',
                marginBottom: '15px',
                marginTop: '0',
                fontFamily: 'Satoshi, sans-serif',
                fontWeight: '900',
                fontSize: '20px'
              }}>
                {getRandomName(profile.demographics.gender, index)}
              </h3>

              <img
                src={getProfileImage(profile.demographics)}
                alt="Customer Profile"
                style={{
                  width: '150px',
                  height: '180px',
                  objectFit: 'cover',
                  marginBottom: '15px'
                }}
              />

              {/* Demographics */}
              {profile.demographics && Object.keys(profile.demographics).length > 0 && (
                <div
                  style={{
                    backgroundColor: '#FFFFFF',
                    padding: '20px 24px',
                    borderRadius: '10px',
                    border: '1px solid #E5E0F3',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                    marginBottom: '20px'
                  }}
                >
                  {Object.entries(profile.demographics).map(([key, value]) => (
                    <div
                      key={key}
                      style={{
                        display: 'flex',
                        alignItems: 'baseline',
                        fontFamily: 'Satoshi, sans-serif',
                        gap: '8px'
                      }}
                    >
                      <span
                        style={{
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          fontSize: '14px',
                          color: '#2B2140'
                        }}
                      >
                        {key === 'employment_status' ? 'EMPLOYMENT:' : `${key.replace(/_/g, ' ')}:`}
                      </span>
                      <span
                        style={{
                          fontSize: '15px',
                          color: '#6C5A87'
                        }}
                      >
                        {value}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {/* Tags */}
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '8px',
                justifyContent: 'flex-start'
              }}>
                {profile.tags.map((tag, tagIndex) => {
                  return (
                    <span key={tagIndex} style={{
                      backgroundColor: '#e7eeff',
                      color: '#a3aaba',
                      padding: '6px 10px',
                      borderRadius: '12px',
                      fontSize: '12px',
                      fontWeight: '600',
                      fontFamily: 'Satoshi, sans-serif',
                      display: 'inline-block'
                    }}>
                      {tag}
                    </span>
                  );
                })}
              </div>
            </div>

            {/* Ask Question Button */}
            <button style={{
              backgroundColor: '#d2d3ff',
              color: '#2B2140',
              padding: '12px 24px',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: '600',
              fontFamily: 'Satoshi, sans-serif',
              border: 'none',
              cursor: 'pointer',
              width: '100%',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#b8b9f5'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#d2d3ff'
            }}
            onClick={() => {
              setIsAnimating(true)
              setSelectedCustomer(index)
              setTimeout(() => {
                setChatMode(true)
                setIsAnimating(false)
              }, 600)
            }}>
              Ask Question
            </button>
          </div>
        ))}

        {/* Chat Mode Layout */}
        {chatMode && selectedCustomer !== null && (() => {
          const profile = getCustomerProfiles()[selectedCustomer]
          return (
            <>
              {/* Selected Customer Card - Column 1 */}
              <div style={{
                backgroundColor: '#F7F7F9',
                padding: '1.5vh 1.5vw 2vh 1.5vw',
                borderRadius: '12px',
                boxShadow: '0 2px 8px rgba(125, 42, 221, 0.1)',
                border: '1px solid #E5E0F3',
                minHeight: '75vh',
                animation: 'slideIn 0.6s ease-in-out',
                position: 'relative'
              }}>
                {/* Percentage Badge in Top Right */}
                {profile.percentage !== undefined && (
                  <div style={{
                    position: 'absolute',
                    top: '12px',
                    right: '12px',
                    backgroundColor: '#7D2ADD',
                    color: '#FFFFFF',
                    padding: '6px 12px',
                    borderRadius: '20px',
                    fontSize: '14px',
                    fontWeight: '700',
                    fontFamily: 'Satoshi, sans-serif',
                    boxShadow: '0 2px 6px rgba(125, 42, 221, 0.3)',
                    zIndex: 10
                  }}>
                    {profile.percentage}%
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{
                    color: '#2B2140',
                    textAlign: 'left',
                    marginBottom: '15px',
                    marginTop: '0',
                    fontFamily: 'Satoshi, sans-serif',
                    fontWeight: '900',
                    fontSize: '20px'
                  }}>
                    {getRandomName(profile.demographics.gender, selectedCustomer)}
                  </h3>
                  <button
                    onClick={() => {
                      setChatMode(false)
                      setSelectedCustomer(null)
                      setChatHistory([])
                      setSessionId(null)
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#7D2ADD',
                      cursor: 'pointer',
                      fontSize: '24px',
                      padding: '0',
                      fontWeight: 'bold'
                    }}
                  >
                    ×
                  </button>
                </div>

                <img
                  src={getProfileImage(profile.demographics)}
                  alt="Customer Profile"
                  style={{
                    width: '150px',
                    height: '180px',
                    objectFit: 'cover',
                    marginBottom: '15px'
                  }}
                />

                {/* Demographics */}
                {profile.demographics && Object.keys(profile.demographics).length > 0 && (
                  <div
                    style={{
                      backgroundColor: '#FFFFFF',
                      padding: '20px 24px',
                      borderRadius: '10px',
                      border: '1px solid #E5E0F3',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px',
                      marginBottom: '20px'
                    }}
                  >
                    {Object.entries(profile.demographics).map(([key, value]) => (
                      <div
                        key={key}
                        style={{
                          display: 'flex',
                          alignItems: 'baseline',
                          fontFamily: 'Satoshi, sans-serif',
                          gap: '8px'
                        }}
                      >
                        <span
                          style={{
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            fontSize: '14px',
                            color: '#2B2140'
                          }}
                        >
                          {key === 'employment_status' ? 'EMPLOYMENT:' : `${key.replace(/_/g, ' ')}:`}
                        </span>
                        <span
                          style={{
                            fontSize: '15px',
                            color: '#6C5A87'
                          }}
                        >
                          {value}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Tags */}
                <div style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '8px',
                  justifyContent: 'flex-start'
                }}>
                  {profile.tags.map((tag, tagIndex) => {
                    return (
                      <span key={tagIndex} style={{
                        backgroundColor: '#e7eeff',
                        color: '#a3aaba',
                        padding: '6px 10px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: '600',
                        fontFamily: 'Satoshi, sans-serif',
                        display: 'inline-block'
                      }}>
                        {tag}
                      </span>
                    );
                  })}
                </div>
              </div>

              {/* Chat Box - Columns 2, 3 & 4 */}
              <div style={{
                backgroundColor: '#F7F7F9',
                padding: '1.5vh 1.5vw 2vh 1.5vw',
                borderRadius: '12px',
                boxShadow: '0 2px 8px rgba(125, 42, 221, 0.1)',
                border: '1px solid #E5E0F3',
                minHeight: '75vh',
                display: 'flex',
                flexDirection: 'column',
                animation: 'fadeIn 0.6s ease-in-out'
              }}>
                <h3 style={{
                  color: '#2B2140',
                  textAlign: 'left',
                  marginBottom: '15px',
                  marginTop: '0',
                  fontFamily: 'Satoshi, sans-serif',
                  fontWeight: '900',
                  fontSize: '20px'
                }}>
                  Chat with {getRandomName(profile.demographics.gender, selectedCustomer)}
                </h3>

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
                      fontFamily: 'Satoshi, sans-serif',
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
                          fontFamily: 'Satoshi, sans-serif',
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
                      fontFamily: 'Satoshi, sans-serif',
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
                      fontFamily: 'Satoshi, sans-serif',
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
                      fontWeight: '600',
                      fontFamily: 'Satoshi, sans-serif',
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
            <h3 style={{ textAlign: 'left', marginBottom: '15px', color: '#2B2140', marginTop: '0', fontFamily: 'Satoshi, sans-serif', fontWeight: '900' }}>Gender Distribution</h3>
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
            <h3 style={{ textAlign: 'left', marginBottom: '0', color: '#2B2140', marginTop: '0', fontFamily: 'Satoshi, sans-serif', fontWeight: '900', padding: '1.5vh 1.5vw 0 1.5vw' }}>Age Distribution</h3>
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
