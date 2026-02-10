/**
 * UserProfile Component
 *
 * Main user profile display showing user info, statistics summary,
 * and last interaction time.
 */

import React from 'react';
import clsx from 'clsx';
import {
  FiAward,
  FiCalendar,
  FiClock,
  FiMessageSquare,
  FiSettings,
  FiStar,
} from 'react-icons/fi';
import type { UserProfile as UserProfileType } from '../../types';
import { formatterService } from '../../services/formatter.service';

interface UserProfileProps {
  profile: UserProfileType;
  showSettings?: boolean;
  onSettingsClick?: () => void;
  compact?: boolean;
  className?: string;
}

interface ProfileHeaderProps {
  userId: string;
  onSettingsClick?: () => void;
  showSettings?: boolean;
}

interface StatItemProps {
  icon: React.ReactNode;
  value: string | number;
  label: string;
  color?: string;
}

function getAvatarInitials(userId: string): string {
  const parts = userId.replace(/[_-]/g, ' ').split(' ');
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return userId.slice(0, 2).toUpperCase();
}

function getAvatarColor(userId: string): string {
  const colors = [
    'bg-purple-500',
    'bg-blue-500',
    'bg-green-500',
    'bg-yellow-500',
    'bg-red-500',
    'bg-indigo-500',
    'bg-pink-500',
    'bg-teal-500',
  ];
  const index = userId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[index % colors.length];
}

const ProfileHeader: React.FC<ProfileHeaderProps> = ({
  userId,
  onSettingsClick,
  showSettings = true,
}) => {
  return (
    <div className="flex items-center gap-4">
      <div
        className={clsx(
          'w-16 h-16 rounded-full flex items-center justify-center text-white font-bold text-xl',
          getAvatarColor(userId)
        )}
      >
        {getAvatarInitials(userId)}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h2 className="font-bold text-lg text-gray-800 dark:text-gray-200 truncate">{userId}</h2>
          {showSettings && onSettingsClick && (
            <button
              onClick={onSettingsClick}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            >
              <FiSettings className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const StatItem: React.FC<StatItemProps> = ({ icon, value, label, color = 'text-gray-500' }) => (
  <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
    <div className={clsx('w-5 h-5 mx-auto mb-1', color)}>{icon}</div>
    <p className="font-bold text-lg text-gray-800 dark:text-gray-200">{value}</p>
    <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
  </div>
);

export const UserProfile: React.FC<UserProfileProps> = ({
  profile,
  showSettings = true,
  onSettingsClick,
  compact = false,
  className,
}) => {
  const lastInteractionText = profile.lastInteraction
    ? formatterService.formatRelativeTime(profile.lastInteraction)
    : 'Нет данных';

  if (compact) {
    return (
      <div
        className={clsx(
          'flex items-center gap-3 p-3 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700',
          className
        )}
      >
        <div
          className={clsx(
            'w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm',
            getAvatarColor(profile.userId)
          )}
        >
          {getAvatarInitials(profile.userId)}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm text-gray-800 dark:text-gray-200 truncate">{profile.userId}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {profile.totalQuestions} вопросов • ★ {profile.averageRating.toFixed(1)}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={clsx(
        'bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden',
        className
      )}
    >
      <div className="bg-gradient-to-r from-purple-500 to-indigo-500 p-6 text-white">
        <ProfileHeader userId={profile.userId} showSettings={showSettings} onSettingsClick={onSettingsClick} />
      </div>

      <div className="p-4">
        <div className="grid grid-cols-4 gap-2">
          <StatItem icon={<FiMessageSquare />} value={profile.totalQuestions} label="Вопросов" color="text-blue-500" />
          <StatItem icon={<FiStar />} value={profile.averageRating.toFixed(1)} label="Рейтинг" color="text-yellow-500" />
          <StatItem icon={<FiAward />} value={profile.primaryInterests.length} label="Интересов" color="text-purple-500" />
          <StatItem icon={<FiClock />} value={Object.keys(profile.topStates).length} label="Состояний" color="text-green-500" />
        </div>

        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <FiCalendar className="w-4 h-4" />
              Последняя активность
            </span>
            <span className="text-gray-700 dark:text-gray-300 font-medium">{lastInteractionText}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

interface ProfileCardMiniProps {
  userId: string;
  totalQuestions?: number;
  className?: string;
}

export const ProfileCardMini: React.FC<ProfileCardMiniProps> = ({
  userId,
  totalQuestions = 0,
  className,
}) => {
  return (
    <div
      className={clsx(
        'p-3 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 rounded-lg',
        className
      )}
    >
      <div className="flex items-center gap-3">
        <div
          className={clsx(
            'w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-xs',
            getAvatarColor(userId)
          )}
        >
          {getAvatarInitials(userId)}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm text-gray-800 dark:text-gray-200 truncate">{userId}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-gray-500">{totalQuestions} вопросов</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;
