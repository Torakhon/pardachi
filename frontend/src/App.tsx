import { useEffect } from 'react'
import type { ReactNode } from 'react'
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
import { TeamDetailPage } from './pages/TeamDetail'
import { TeamsPage } from './pages/Teams'
import { UsersPage } from './pages/Users'
import { useAuth } from './store/auth'

export default function App() {
  const { status, user, isAdmin, canWrite } = useAuth()
  const location = useLocation()

  // Sahifa almashganda tepaga qaytamiz (mobil UX).
  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [location.pathname])

  if (status === 'loading') return <FullScreenLoader message={t.auth.signingIn} />
  if (status !== 'authenticated' || !user) return <LoginPage />

  // Ko'ruvchi rolidagi foydalanuvchi yozish sahifalariga kira olmaydi.
  const write = (element: ReactNode) => (canWrite ? element : <Navigate to="/" replace />)

  return (
    <>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/new" element={write(<ProjectFormPage mode="create" />)} />
        <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="/projects/:projectId/edit" element={write(<ProjectFormPage mode="edit" />)} />
        <Route path="/projects/:projectId/measurements" element={<ProjectMeasurementsPage />} />
        <Route path="/projects/:projectId/rooms/new" element={write(<RoomFormPage mode="create" />)} />
        <Route path="/rooms/:roomId" element={<RoomDetailPage />} />
        <Route path="/rooms/:roomId/edit" element={write(<RoomFormPage mode="edit" />)} />
        <Route path="/rooms/:roomId/items/new" element={write(<MeasurementFormPage mode="create" />)} />
        <Route path="/measurements/:itemId/edit" element={write(<MeasurementFormPage mode="edit" />)} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/teams" element={isAdmin ? <TeamsPage /> : <Navigate to="/" replace />} />
        <Route path="/teams/:teamId" element={<TeamDetailPage />} />
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
