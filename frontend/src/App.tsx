import { useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { Button } from './components/Button'
import { EmptyState, FullScreenLoader } from './components/Feedback'
import { BottomNav, Screen } from './components/Layout'
import { t } from './i18n/uz'
import { DashboardPage } from './pages/Dashboard'
import { LoginPage } from './pages/Login'
import { MeasurementFormPage } from './pages/MeasurementForm'
import { ProfilePage } from './pages/Profile'
import { ProjectDetailPage } from './pages/ProjectDetail'
import { ProjectFormPage } from './pages/ProjectForm'
import { ProjectMeasurementsPage } from './pages/ProjectMeasurements'
import { ProjectsPage } from './pages/Projects'
import { RoomDetailPage } from './pages/RoomDetail'
import { RoomFormPage } from './pages/RoomForm'
import { UsersPage } from './pages/Users'
import { useAuth } from './store/auth'

export default function App() {
  const { status, user, isAdmin } = useAuth()
  const location = useLocation()

  // Sahifa almashganda tepaga qaytamiz (mobil UX).
  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [location.pathname])

  if (status === 'loading') return <FullScreenLoader message={t.auth.signingIn} />
  if (status !== 'authenticated' || !user) return <LoginPage />

  return (
    <>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/new" element={<ProjectFormPage mode="create" />} />
        <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="/projects/:projectId/edit" element={<ProjectFormPage mode="edit" />} />
        <Route path="/projects/:projectId/measurements" element={<ProjectMeasurementsPage />} />
        <Route path="/projects/:projectId/rooms/new" element={<RoomFormPage mode="create" />} />
        <Route path="/rooms/:roomId" element={<RoomDetailPage />} />
        <Route path="/rooms/:roomId/edit" element={<RoomFormPage mode="edit" />} />
        <Route path="/rooms/:roomId/items/new" element={<MeasurementFormPage mode="create" />} />
        <Route path="/measurements/:itemId/edit" element={<MeasurementFormPage mode="edit" />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/users" element={isAdmin ? <UsersPage /> : <Navigate to="/" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>

      <BottomNav isAdmin={isAdmin} />
    </>
  )
}

function NotFoundPage() {
  return (
    <Screen>
      <EmptyState
        icon="🧭"
        title="Sahifa topilmadi"
        description="Manzil noto‘g‘ri yoki sahifa o‘chirilgan."
        action={
          <Button size="sm" onClick={() => window.history.back()}>
            {t.app.back}
          </Button>
        }
      />
    </Screen>
  )
}
