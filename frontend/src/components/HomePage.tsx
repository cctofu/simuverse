import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

function HomePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [productInput, setProductInput] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isFocused, setIsFocused] = useState(false)

  // Pre-fill input from URL parameter if present
  useEffect(() => {
    const productFromUrl = searchParams.get('product')
    if (productFromUrl) {
      setProductInput(productFromUrl)
    }
  }, [searchParams])

  const handleGenerateResponse = () => {
    if (!productInput.trim()) {
      setError("Please enter a product description")
      return
    }
    navigate(`/search?product=${encodeURIComponent(productInput)}`)
  }

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
      left: 0,
      padding: '20px',
      boxSizing: 'border-box'
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

        @media (max-width: 768px) {
          .glass-card {
            width: 90% !important;
            padding: 30px !important;
            max-width: 500px !important;
          }

          .logo-text {
            font-size: 48px !important;
          }

          .subtitle-text {
            font-size: 14px !important;
          }
        }
      `}</style>

      {/* Aurora gradient orbs */}
      <div className="aurora-orb-1"></div>
      <div className="aurora-orb-2"></div>
      <div className="aurora-orb-3"></div>

      <div className="glass-card" style={{
        width: '700px',
        maxWidth: '90%',
        backgroundColor: 'rgba(255, 255, 255, 0.7)',
        backdropFilter: 'blur(40px)',
        WebkitBackdropFilter: 'blur(40px)',
        padding: '50px',
        borderRadius: '24px',
        boxShadow: '0 20px 60px rgba(139, 92, 246, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.8)',
        border: '1px solid rgba(255, 255, 255, 0.9)',
        fontFamily: 'Comfortaa, sans-serif',
        boxSizing: 'border-box',
        position: 'relative',
        zIndex: 1
      }}>
        {/* Logo */}
        
        <h1 className="logo-text" style={{
          color: '#9860d7ff',
          fontSize: '64px',
          fontWeight: '700',
          letterSpacing: '2px',
          margin: 0,
          fontFamily: 'Akira, sans-serif'
        }}>
          Simuverse
        </h1>

        {/* Subtitle */}
        <p className="subtitle-text" style={{
          color: '#475569',
          fontSize: '18px',
          fontWeight: '400',
          textAlign: 'center',
          margin: '0 0 40px 0',
          lineHeight: '1.6',
          fontFamily: 'Comfortaa, sans-serif'
        }}>
          AI-Powered Simulation for Pre-Market Product Validation
        </p>

        {/* Input Field */}
        <textarea
          id="product-input"
          value={productInput}
          onChange={(e) => setProductInput(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Describe your product here..."
          style={{
            width: '100%',
            minHeight: '180px',
            padding: '20px',
            fontSize: '16px',
            backgroundColor: '#FFFFFF',
            color: '#1E293B',
            border: isFocused
              ? '2px solid #8B5CF6'
              : '2px solid #E2E8F0',
            borderRadius: '16px',
            resize: 'vertical',
            fontFamily: 'inherit',
            lineHeight: '1.6',
            boxSizing: 'border-box',
            outline: 'none',
            transition: 'all 0.3s ease',
            boxShadow: isFocused
              ? '0 0 0 4px rgba(139, 92, 246, 0.1), 0 4px 12px rgba(0, 0, 0, 0.05)'
              : '0 2px 8px rgba(0, 0, 0, 0.04)'
          }}
        />

        {error && (
          <div style={{
            marginTop: '20px',
            padding: '15px 20px',
            color: '#DC2626',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            borderRadius: '12px',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            fontSize: '15px'
          }}>
            {error}
          </div>
        )}

        {/* Gradient CTA Button */}
        <button
          onClick={handleGenerateResponse}
          style={{
            marginTop: '30px',
            width: '100%',
            padding: '18px 40px',
            fontSize: '20px',
            fontWeight: '700',
            fontFamily: 'Comfortaa, sans-serif',
            background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 50%, #6D28D9 100%)',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: '14px',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            boxShadow: '0 8px 24px rgba(139, 92, 246, 0.4), 0 4px 12px rgba(0, 0, 0, 0.2)',
            position: 'relative',
            overflow: 'hidden'
          }}
          onMouseOver={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)'
            e.currentTarget.style.boxShadow = '0 12px 32px rgba(139, 92, 246, 0.5), 0 6px 16px rgba(0, 0, 0, 0.3)'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = '0 8px 24px rgba(139, 92, 246, 0.4), 0 4px 12px rgba(0, 0, 0, 0.2)'
          }}
        >
          Generate Responses ✨
        </button>
      </div>
    </div>
  )
}

export default HomePage
