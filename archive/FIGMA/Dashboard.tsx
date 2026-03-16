import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { ProgressBar } from '../components/ProgressBar';
import { BadgeCard } from '../components/BadgeCard';
import { loadUserProgress, loadSubscription, getUsername, getSpecialty } from '../utils/storage';
import type { UserProgress, UserSubscription } from '../types';
import { BookOpen, Target, Flame, Trophy, Crown, TrendingUp } from 'lucide-react';

export function Dashboard() {
  const navigate = useNavigate();
  const [progress, setProgress] = useState<UserProgress | null>(null);
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [username, setUsername] = useState('');
  const [specialty, setSpecialty] = useState('');

  useEffect(() => {
    setProgress(loadUserProgress());
    setSubscription(loadSubscription());
    setUsername(getUsername());
    setSpecialty(getSpecialty());
  }, []);

  if (!progress || !subscription) return null;

  const recentBadges = progress.badges.slice(-3).reverse();

  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Welcome back, {username}!</h1>
          <p className="text-muted-foreground">{specialty}</p>
        </div>
        {subscription.tier === 'free' && (
          <Button
            onClick={() => navigate('/upgrade')}
            className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
          >
            <Crown className="w-4 h-4 mr-2" />
            Upgrade to Premium
          </Button>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Level</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{progress.level}</div>
            <p className="text-xs text-muted-foreground">
              {progress.xp} / {progress.xpToNextLevel} XP
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cases Completed</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{progress.completedCases}</div>
            <p className="text-xs text-muted-foreground">Total interpretations</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Accuracy</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{progress.accuracy.toFixed(1)}%</div>
            <p className="text-xs text-muted-foreground">Overall performance</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current Streak</CardTitle>
            <Flame className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{progress.currentStreak}</div>
            <p className="text-xs text-muted-foreground">
              Longest: {progress.longestStreak} days
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Continue Learning</CardTitle>
            <CardDescription>Practice ABG interpretation at your level</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ProgressBar
              current={progress.xp}
              total={progress.xpToNextLevel}
              label="Progress to Next Level"
            />
            <div className="grid grid-cols-2 gap-3">
              <Button onClick={() => navigate('/learn')} className="w-full">
                <BookOpen className="w-4 h-4 mr-2" />
                Learn Mode
              </Button>
              <Button onClick={() => navigate('/practice')} variant="outline" className="w-full">
                <Target className="w-4 h-4 mr-2" />
                Practice
              </Button>
            </div>
            {subscription.tier !== 'pro' && (
              <div className="text-sm text-muted-foreground text-center">
                {subscription.casesRemainingToday} case{subscription.casesRemainingToday !== 1 ? 's' : ''} remaining today
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="w-5 h-5" />
              Recent Badges
            </CardTitle>
            <CardDescription>Your latest achievements</CardDescription>
          </CardHeader>
          <CardContent>
            {recentBadges.length > 0 ? (
              <div className="grid grid-cols-3 gap-3">
                {recentBadges.map((badge) => (
                  <BadgeCard key={badge.id} badge={badge} />
                ))}
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-8">
                Complete cases to earn badges!
              </div>
            )}
            <Button
              onClick={() => navigate('/profile')}
              variant="outline"
              className="w-full mt-4"
            >
              View All Badges
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Difficulty Levels */}
      <Card>
        <CardHeader>
          <CardTitle>Difficulty Levels</CardTitle>
          <CardDescription>Unlock new challenges as you progress</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { name: 'Beginner', level: 1, color: 'bg-green-500' },
              { name: 'Intermediate', level: 5, color: 'bg-blue-500' },
              { name: 'Advanced', level: 10, color: 'bg-purple-500' },
              { name: 'Master', level: 20, color: 'bg-red-500', requiresPro: true },
            ].map((difficulty) => {
              const unlocked = progress.level >= difficulty.level;
              const requiresPro = difficulty.requiresPro && !subscription.hasAccessToMaster;

              return (
                <div
                  key={difficulty.name}
                  className={`p-4 rounded-lg border-2 ${
                    unlocked && !requiresPro
                      ? 'border-primary bg-primary/5'
                      : 'border-muted bg-muted/50 opacity-60'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-3 h-3 rounded-full ${difficulty.color}`} />
                    <span className="font-medium">{difficulty.name}</span>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {!unlocked ? `Unlock at Level ${difficulty.level}` :
                     requiresPro ? 'Requires Pro' : 'Unlocked'}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
