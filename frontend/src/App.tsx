import { Routes, Route } from 'react-router-dom'
import HomePage from './components/HomePage'
import SearchPage from './components/SearchPage'
import './App.css'

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/search" element={<SearchPage />} />
    </Routes>
  )
}

export default App
