import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ChatPage } from './pages/ChatPage'
import { ImprovePage } from './pages/ImprovePage'
import { OverviewPage } from './pages/OverviewPage'
import { ScorePage } from './pages/ScorePage'
import { TrackerPage } from './pages/TrackerPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<OverviewPage />} />
        <Route path="score" element={<ScorePage />} />
        <Route path="improve" element={<ImprovePage />} />
        <Route path="assistant" element={<ChatPage />} />
        <Route path="tracker" element={<TrackerPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
