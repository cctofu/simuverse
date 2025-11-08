import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function HomePage() {
  const navigate = useNavigate()
  const [productInput, setProductInput] = useState("")
  const [error, setError] = useState<string | null>(null)

  const handleGenerateResponse = () => {
    if (!productInput.trim()) {
      setError("Please enter a product description")
      return
    }
    navigate(`/search?product=${encodeURIComponent(productInput)}`)
  }

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
        textAlign: 'center',
        marginBottom: '60px',
        color: '#000000',
        fontSize: '96px',
        fontWeight: '700',
        letterSpacing: '4px',
        fontFamily: 'Akira, sans-serif'
      }}>
        Mirra
      </h1>

      <div style={{
        width: '700px',
        backgroundColor: '#f2f1ef',
        padding: '50px',
        borderRadius: '16px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
        fontFamily: 'Satoshi, sans-serif'
      }}>
        <label htmlFor="product-input" style={{
          display: 'block',
          marginBottom: '20px',
          color: '#000000',
          fontSize: '20px',
          fontWeight: '600'
        }}>
          Product Description
        </label>

        <textarea
          id="product-input"
          value={productInput}
          onChange={(e) => setProductInput(e.target.value)}
          placeholder="Enter your product description here..."
          style={{
            width: '100%',
            minHeight: '200px',
            padding: '20px',
            fontSize: '16px',
            backgroundColor: '#ffffff',
            color: '#000000',
            border: '1px solid #cccccc',
            borderRadius: '10px',
            resize: 'vertical',
            fontFamily: 'inherit',
            lineHeight: '1.6',
            boxSizing: 'border-box'
          }}
        />

        {error && (
          <div style={{
            marginTop: '20px',
            padding: '15px',
            color: '#ff6b6b',
            backgroundColor: '#2a2a2a',
            borderRadius: '8px',
            border: '1px solid #ff6b6b',
            fontSize: '15px'
          }}>
            {error}
          </div>
        )}

        <button
          onClick={handleGenerateResponse}
          style={{
            marginTop: '30px',
            width: '100%',
            padding: '18px 40px',
            fontSize: '20px',
            fontWeight: '600',
            backgroundColor: '#ff9900',
            color: '#000000',
            border: 'none',
            borderRadius: '10px',
            cursor: 'pointer',
            transition: 'background-color 0.2s'
          }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#cc7a00'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#ff9900'}
        >
          Generate Response
        </button>
      </div>
    </div>
  )
}

export default HomePage
