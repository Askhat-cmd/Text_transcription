/**
 * HomePage Component
 * 
 * Landing page with welcome message, quick start, and features overview.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FiMessageSquare, 
  FiTrendingUp, 
  FiUsers, 
  FiStar,
  FiArrowRight,
  FiGithub,
  FiBookOpen
} from 'react-icons/fi';
import clsx from 'clsx';
import { storageService } from '../services/storage.service';

// ===== TYPES =====

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  color: string;
}

// ===== FEATURE CARD =====

const FeatureCard: React.FC<FeatureCardProps> = ({ icon, title, description, color }) => (
  <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm hover:shadow-md transition-all duration-200 border border-gray-200 dark:border-gray-700">
    <div className={clsx('w-12 h-12 rounded-lg flex items-center justify-center mb-4', color)}>
      {icon}
    </div>
    <h3 className="font-semibold text-lg text-gray-800 dark:text-gray-200 mb-2">
      {title}
    </h3>
    <p className="text-sm text-gray-600 dark:text-gray-400">
      {description}
    </p>
  </div>
);

// ===== MAIN COMPONENT =====

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const hasApiKey = storageService.hasApiKey();
  const userId = storageService.getUserId();

  const handleQuickStart = () => {
    if (hasApiKey && userId) {
      navigate('/chat');
    } else {
      navigate('/settings');
    }
  };

  const features = [
    {
      icon: <FiMessageSquare className="w-6 h-6 text-white" />,
      title: 'Адаптивный диалог',
      description: 'ИИ анализирует ваше состояние и адаптирует ответы под ваш уровень понимания.',
      color: 'bg-purple-500',
    },
    {
      icon: <FiTrendingUp className="w-6 h-6 text-white" />,
      title: 'Персональный путь',
      description: 'Получайте рекомендации по развитию и отслеживайте прогресс трансформации.',
      color: 'bg-indigo-500',
    },
    {
      icon: <FiBookOpen className="w-6 h-6 text-white" />,
      title: 'База знаний',
      description: 'Доступ к структурированным материалам с прямыми ссылками на источники.',
      color: 'bg-blue-500',
    },
    {
      icon: <FiUsers className="w-6 h-6 text-white" />,
      title: 'Уровни сложности',
      description: 'Выбирайте уровень: начинающий, средний или продвинутый.',
      color: 'bg-green-500',
    },
    {
      icon: <FiStar className="w-6 h-6 text-white" />,
      title: 'Обратная связь',
      description: 'Оценивайте ответы, чтобы система лучше понимала ваши потребности.',
      color: 'bg-yellow-500',
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-900 dark:to-purple-900/20">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-5 dark:opacity-10">
          <div className="absolute top-20 left-20 w-72 h-72 bg-purple-500 rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-20 w-72 h-72 bg-indigo-500 rounded-full blur-3xl" />
        </div>

        <div className="relative max-w-6xl mx-auto px-4 py-20">
          <div className="text-center">
            {/* Logo/Title */}
            <h1 className="text-5xl md:text-6xl font-bold text-gray-900 dark:text-white mb-6">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-indigo-600">
                Bot Psychologist
              </span>
            </h1>
            
            <p className="text-xl md:text-2xl text-gray-600 dark:text-gray-300 mb-4 max-w-2xl mx-auto">
              Адаптивный QA-бот для личностной трансформации
            </p>
            
            <p className="text-base text-gray-500 dark:text-gray-400 mb-8 max-w-xl mx-auto">
              Задавайте вопросы, получайте персонализированные ответы и следуйте 
              индивидуальному пути развития на основе ваших состояний и интересов.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={handleQuickStart}
                className={clsx(
                  'inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl',
                  'bg-gradient-to-r from-purple-600 to-indigo-600',
                  'text-white font-semibold text-lg',
                  'hover:from-purple-700 hover:to-indigo-700',
                  'transform hover:scale-105 transition-all duration-200',
                  'shadow-lg hover:shadow-xl'
                )}
              >
                {hasApiKey ? 'Перейти к чату' : 'Начать'}
                <FiArrowRight className="w-5 h-5" />
              </button>

              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className={clsx(
                  'inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl',
                  'bg-white dark:bg-gray-800',
                  'text-gray-700 dark:text-gray-300 font-semibold text-lg',
                  'border border-gray-200 dark:border-gray-700',
                  'hover:bg-gray-50 dark:hover:bg-gray-750',
                  'transition-all duration-200'
                )}
              >
                <FiGithub className="w-5 h-5" />
                GitHub
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="max-w-6xl mx-auto px-4 py-16">
        <h2 className="text-3xl font-bold text-center text-gray-900 dark:text-white mb-4">
          Возможности
        </h2>
        <p className="text-center text-gray-600 dark:text-gray-400 mb-12 max-w-2xl mx-auto">
          Умный бот, который понимает ваше состояние и помогает в личностном развитии
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, idx) => (
            <FeatureCard key={idx} {...feature} />
          ))}
        </div>
      </div>

      {/* How It Works Section */}
      <div className="bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm py-16">
        <div className="max-w-6xl mx-auto px-4">
          <h2 className="text-3xl font-bold text-center text-gray-900 dark:text-white mb-12">
            Как это работает
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'Настройте', desc: 'Введите API ключ и выберите уровень сложности' },
              { step: '02', title: 'Спросите', desc: 'Задавайте вопросы о трансформации и развитии' },
              { step: '03', title: 'Развивайтесь', desc: 'Получайте персональные рекомендации и следуйте пути' },
            ].map((item, idx) => (
              <div key={idx} className="text-center">
                <div className="w-16 h-16 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 flex items-center justify-center mx-auto mb-4">
                  <span className="text-white font-bold text-xl">{item.step}</span>
                </div>
                <h3 className="font-semibold text-lg text-gray-800 dark:text-gray-200 mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        <p>Bot Psychologist v0.6.0 • Phase 6: Web UI</p>
        <p className="mt-1">Powered by FastAPI + React + TypeScript</p>
      </footer>
    </div>
  );
};

export default HomePage;


