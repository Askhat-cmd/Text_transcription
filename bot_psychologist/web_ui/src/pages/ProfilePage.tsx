/**
 * ProfilePage Component
 *
 * User profile page with history, interests, and statistics.
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { FiArrowLeft, FiMessageSquare, FiRefreshCw } from 'react-icons/fi';
import clsx from 'clsx';
import { UserProfile, InterestsCard, StatisticsCard } from '../components/profile';
import { Loader } from '../components/common';
import { apiService } from '../services/api.service';
import { storageService } from '../services/storage.service';
import type { UserHistoryResponse, UserProfile as UserProfileType } from '../types';

const ProfilePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const urlUserId = searchParams.get('user_id');
  const userId = urlUserId || storageService.getUserId();

  const [history, setHistory] = useState<UserHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async () => {
    if (!userId) {
      setError('User ID is missing');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await apiService.getUserHistory(userId, 50);
      setHistory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load user history');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [userId]);

  const profileData: UserProfileType | null = history ? {
    userId: history.user_id,
    totalQuestions: history.total_turns,
    primaryInterests: history.primary_interests,
    averageRating: history.average_rating,
    topStates: buildTopStates(history.turns),
    lastInteraction: history.last_interaction ? new Date(history.last_interaction) : undefined,
  } : null;

  const ratingDistribution = history ? buildRatingDistribution(history.turns) : {};

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loader size="lg" text="Loading profile..." />
      </div>
    );
  }

  if (error || !profileData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error || 'Profile was not found'}</p>
          <button
            onClick={() => navigate(`/chat?user_id=${encodeURIComponent(userId)}&open_settings=1`)}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700"
          >
            Go to settings
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <FiArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="font-semibold text-lg text-gray-800 dark:text-gray-200">Profile</h1>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchHistory}
              disabled={isLoading}
              className={clsx(
                'p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors',
                isLoading && 'animate-spin'
              )}
            >
              <FiRefreshCw className="w-5 h-5" />
            </button>
            <button
              onClick={() => navigate(`/chat?user_id=${userId}`)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
            >
              <FiMessageSquare className="w-4 h-4" />
              <span className="hidden sm:inline">Chat</span>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <UserProfile
          profile={profileData}
          showSettings
          onSettingsClick={() => navigate(`/chat?user_id=${encodeURIComponent(userId)}&open_settings=1`)}
        />

        <InterestsCard
          primaryInterests={profileData.primaryInterests}
          topConcepts={extractTopConcepts(history?.turns || [])}
        />

        <StatisticsCard
          totalTurns={profileData.totalQuestions}
          topStates={profileData.topStates}
          ratingDistribution={ratingDistribution}
          averageRating={profileData.averageRating}
        />

        {history && history.turns.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="font-semibold text-gray-800 dark:text-gray-200 mb-4">Recent questions</h3>
            <div className="space-y-3">
              {history.turns.slice(0, 5).map((turn, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                >
                  <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">{turn.user_input}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(turn.timestamp).toLocaleDateString('ru-RU')}
                    {turn.user_state && ` • ${turn.user_state}`}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

function buildTopStates(turns: UserHistoryResponse['turns']): Record<string, number> {
  const states: Record<string, number> = {};

  turns.forEach((turn) => {
    if (turn.user_state) {
      states[turn.user_state] = (states[turn.user_state] || 0) + 1;
    }
  });

  return states;
}

function buildRatingDistribution(turns: UserHistoryResponse['turns']): Record<number, number> {
  const distribution: Record<number, number> = {};

  turns.forEach((turn) => {
    if (turn.user_rating && turn.user_rating >= 1 && turn.user_rating <= 5) {
      distribution[turn.user_rating] = (distribution[turn.user_rating] || 0) + 1;
    }
  });

  return distribution;
}

function extractTopConcepts(turns: UserHistoryResponse['turns']): string[] {
  const conceptCounts: Record<string, number> = {};

  turns.forEach((turn) => {
    turn.concepts.forEach((concept) => {
      conceptCounts[concept] = (conceptCounts[concept] || 0) + 1;
    });
  });

  return Object.entries(conceptCounts)
    .sort(([, left], [, right]) => right - left)
    .slice(0, 10)
    .map(([concept]) => concept);
}

export default ProfilePage;
