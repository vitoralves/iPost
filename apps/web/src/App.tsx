import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { Layout } from "./components/Layout"
import { AudioPage } from "./pages/Audio"
import { BrandKitPage } from "./pages/BrandKit"
import { CalendarPage } from "./pages/Calendar"
import { JobDetailPage } from "./pages/JobDetail"
import { SettingsPage } from "./pages/Settings"
import { TodayPage } from "./pages/Today"
import { TopicsPage } from "./pages/Topics"
import { StoreProvider } from "./store"

export default function App() {
  return (
    <StoreProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<TodayPage />} />
            <Route path="/jobs/:id" element={<JobDetailPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/topics" element={<TopicsPage />} />
            <Route path="/audio" element={<AudioPage />} />
            <Route path="/brand-kit" element={<BrandKitPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </StoreProvider>
  )
}
