/**
 * User Types for Bot Psychologist Web UI
 * 
 * Types for user profile and statistics.
 */

export interface UserProfile {
  userId: string;
  totalQuestions: number;
  primaryInterests: string[];
  averageRating: number;
  topStates: Record<string, number>;
  lastInteraction?: Date;
  joinedAt?: Date;
}

export interface UserStats {
  totalUsers: number;
  totalQuestions: number;
  averageProcessingTime: number;
  topStates: Record<string, number>;
  topInterests: string[];
  feedbackStats: Record<string, number>;
}

export interface UserSession {
  userId: string;
  sessionId: string;
  startedAt: Date;
  lastActivityAt: Date;
  messageCount: number;
  currentState?: string;
}

// Aggregated statistics for profile page
export interface UserProfileStats {
  totalMessages: number;
  totalSessions: number;
  averageMessagesPerSession: number;
  mostDiscussedTopics: string[];
  stateHistory: Array<{
    state: string;
    count: number;
    percentage: number;
  }>;
  ratingDistribution: Record<number, number>;
  activityByDay: Record<string, number>;
}


