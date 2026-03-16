import { Outlet, Link, useLocation } from 'react-router';
import { useState, useEffect } from 'react';
import { loadUserProgress, loadSubscription, getUsername } from '../utils/storage';
import type { UserProgress, UserSubscription } from '../types';
import {
  BookOpen,
  Target,
  Trophy,
  User,
  Crown,
  Menu,
  X,
  Home,
  Flame,
} from 'lucide-react';
import { Button } from './ui/button';
import { Progress } from './ui/progress';

export function RootLayout() {
  const location = useLocation();
  const [progress, setProgress] = useState<UserProgress | null>(null);
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [username, setUsername] = useState('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const loadData = () => {
      setProgress(loadUserProgress());
      setSubscription(loadSubscription());
      setUsername(getUsername());
    };
    loadData();

    // Refresh data when route changes
    const interval = setInterval(loadData, 1000);
    return () => clearInterval(interval);
  }, [location]);

  const navigation = [
    { name: 'Dashboard', href: '/', icon: Home },
    { name: 'Learn', href: '/learn', icon: BookOpen },
    { name: 'Practice', href: '/practice', icon: Target },
    { name: 'Leaderboard', href: '/leaderboard', icon: Trophy },
    { name: 'Profile', href: '/profile', icon: User },
  ];

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center px-4">
          <div className="flex items-center gap-2 font-bold text-xl">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center text-white">
              <BookOpen className="w-5 h-5" />
            </div>
            <span className="hidden sm:inline">ABG Master</span>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1 mx-auto">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <Link key={item.name} to={item.href}>
                  <Button
                    variant={isActive(item.href) ? 'default' : 'ghost'}
                    className="gap-2"
                  >
                    <Icon className="w-4 h-4" />
                    {item.name}
                  </Button>
                </Link>
              );
            })}
          </nav>

          {/* User Info */}
          <div className="ml-auto flex items-center gap-4">
            {progress && (
              <div className="hidden lg:flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <Flame className="w-4 h-4 text-orange-500" />
                  <span className="text-sm font-medium">{progress.currentStreak}</span>
                </div>
                <div className="text-sm">
                  <span className="font-medium">Level {progress.level}</span>
                </div>
              </div>
            )}
            {subscription && subscription.tier !== 'free' && (
              <div className="hidden sm:flex items-center gap-1 px-2 py-1 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-bold">
                <Crown className="w-3 h-3" />
                {subscription.tier === 'premium' ? 'PREMIUM' : 'PRO'}
              </div>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
          </div>
        </div>

        {/* XP Bar */}
        {progress && (
          <div className="border-t">
            <div className="container mx-auto px-4 py-2">
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {progress.xp} / {progress.xpToNextLevel} XP
                </span>
                <Progress
                  value={(progress.xp / progress.xpToNextLevel) * 100}
                  className="h-2 flex-1"
                />
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b bg-background">
          <nav className="container mx-auto px-4 py-4 space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <Button
                    variant={isActive(item.href) ? 'default' : 'ghost'}
                    className="w-full justify-start gap-2"
                  >
                    <Icon className="w-4 h-4" />
                    {item.name}
                  </Button>
                </Link>
              );
            })}
          </nav>
        </div>
      )}

      {/* Main Content */}
      <main>
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t mt-12">
        <div className="container mx-auto px-4 py-6">
          <div className="text-center text-sm text-muted-foreground">
            <p>© 2026 ABG Master. All rights reserved.</p>
            <p className="mt-1">
              Educational platform for arterial blood gas interpretation
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
