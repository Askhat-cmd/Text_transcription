/**
 * SettingsPage
 *
 * Legacy route kept for backward compatibility.
 * Redirects to chat and opens the in-chat settings modal.
 */

import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { storageService } from '../services/storage.service';

interface LocationState {
  message?: string;
}

const SettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const state = (location.state as LocationState | null) || null;
    const userId = storageService.getUserId();
    const params = new URLSearchParams({
      user_id: userId,
      open_settings: '1',
    });

    if (state?.message) {
      params.set('settings_notice', state.message);
    }

    navigate(`/chat?${params.toString()}`, { replace: true });
  }, [location.state, navigate]);

  return null;
};

export default SettingsPage;
