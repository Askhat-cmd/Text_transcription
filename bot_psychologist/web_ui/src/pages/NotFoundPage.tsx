/**
 * NotFoundPage Component
 * 
 * 404 error page with navigation back to home.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FiHome, FiMessageSquare, FiArrowLeft } from 'react-icons/fi';
import clsx from 'clsx';

const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-900 dark:to-purple-900/20 px-4">
      <div className="text-center max-w-md">
        {/* 404 Animation */}
        <div className="relative mb-8">
          <div className="text-[150px] font-bold text-purple-100 dark:text-purple-900/30 leading-none">
            404
          </div>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-6xl animate-bounce">🤔</span>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-200 mb-4">
          Страница не найдена
        </h1>

        {/* Description */}
        <p className="text-gray-600 dark:text-gray-400 mb-8">
          Похоже, эта страница ушла на трансформацию и пока не вернулась. 
          Попробуйте начать с главной или перейти в чат.
        </p>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={() => navigate('/')}
            className={clsx(
              'flex items-center justify-center gap-2 px-6 py-3 rounded-xl',
              'bg-gradient-to-r from-purple-600 to-indigo-600',
              'text-white font-medium',
              'hover:from-purple-700 hover:to-indigo-700',
              'transition-all duration-200'
            )}
          >
            <FiHome className="w-5 h-5" />
            На главную
          </button>

          <button
            onClick={() => navigate('/chat')}
            className={clsx(
              'flex items-center justify-center gap-2 px-6 py-3 rounded-xl',
              'bg-white dark:bg-gray-800',
              'text-gray-700 dark:text-gray-300 font-medium',
              'border border-gray-200 dark:border-gray-700',
              'hover:bg-gray-50 dark:hover:bg-gray-750',
              'transition-all duration-200'
            )}
          >
            <FiMessageSquare className="w-5 h-5" />
            В чат
          </button>

          <button
            onClick={() => navigate(-1)}
            className={clsx(
              'flex items-center justify-center gap-2 px-6 py-3 rounded-xl',
              'text-gray-500 dark:text-gray-400 font-medium',
              'hover:text-gray-700 dark:hover:text-gray-200',
              'transition-all duration-200'
            )}
          >
            <FiArrowLeft className="w-5 h-5" />
            Назад
          </button>
        </div>

        {/* Fun fact */}
        <p className="mt-12 text-sm text-gray-400 dark:text-gray-500 italic">
          "Заблудиться — это тоже часть пути" 🧘
        </p>
      </div>
    </div>
  );
};

export default NotFoundPage;


