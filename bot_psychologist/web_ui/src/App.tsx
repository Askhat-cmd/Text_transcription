/**
 * App Component
 * 
 * Main application with routing and theme support.
 */

import { Routes, Route } from 'react-router-dom';
import { useTheme } from './hooks/useTheme';
import { 
  HomePage, 
  ChatPage, 
  ProfilePage, 
  SettingsPage, 
  NotFoundPage 
} from './pages';

function App() {
  const { theme } = useTheme();

  return (
    <div className={theme === 'dark' ? 'dark' : ''}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </div>
  );
}

export default App;


