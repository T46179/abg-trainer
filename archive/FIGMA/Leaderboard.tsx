import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { PremiumGate } from '../components/PremiumGate';
import { loadSubscription, loadUserProgress, getUsername, getSpecialty } from '../utils/storage';
import { generateMockLeaderboard } from '../utils/mock-data';
import type { LeaderboardEntry, UserSubscription, UserProgress } from '../types';
import { Trophy, Medal, Crown, TrendingUp } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

export function Leaderboard() {
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [progress, setProgress] = useState<UserProgress | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [username, setUsername] = useState('');
  const [specialty, setSpecialty] = useState('');

  useEffect(() => {
    setSubscription(loadSubscription());
    setProgress(loadUserProgress());
    setUsername(getUsername());
    setSpecialty(getSpecialty());
    setLeaderboard(generateMockLeaderboard());
  }, []);

  if (!subscription) return null;

  if (!subscription.hasAccessToLeaderboard) {
    return (
      <div className="container mx-auto p-6 max-w-4xl">
        <h1 className="text-3xl font-bold mb-6">Leaderboard</h1>
        <PremiumGate
          feature="Global Leaderboard"
          description="Compare your progress with other medical professionals and compete for the top spot!"
          requiredTier="premium"
        />
      </div>
    );
  }

  const userRank = 15; // Mock user rank
  const userEntry: LeaderboardEntry = {
    rank: userRank,
    username,
    specialty,
    level: progress?.level || 1,
    xp: progress?.xp || 0,
    accuracy: progress?.accuracy || 100,
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=user',
  };

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <Trophy className="w-5 h-5 text-amber-500" />;
    if (rank === 2) return <Medal className="w-5 h-5 text-slate-400" />;
    if (rank === 3) return <Medal className="w-5 h-5 text-amber-700" />;
    return <span className="text-muted-foreground">#{rank}</span>;
  };

  const LeaderboardTable = ({ entries }: { entries: LeaderboardEntry[] }) => (
    <div className="space-y-2">
      {entries.map((entry) => {
        const isUser = entry.rank === userRank;
        return (
          <div
            key={entry.rank}
            className={`flex items-center gap-4 p-4 rounded-lg border ${
              isUser ? 'bg-primary/5 border-primary' : 'bg-card'
            }`}
          >
            <div className="w-12 flex items-center justify-center font-bold">
              {getRankIcon(entry.rank)}
            </div>
            <Avatar className="h-10 w-10">
              <AvatarImage src={entry.avatar} />
              <AvatarFallback>{entry.username.charAt(0)}</AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <div className="font-medium truncate">{entry.username}</div>
              <div className="text-sm text-muted-foreground truncate">{entry.specialty}</div>
            </div>
            <div className="text-right">
              <div className="font-medium">Level {entry.level}</div>
              <div className="text-sm text-muted-foreground">{entry.xp} XP</div>
            </div>
            <div className="text-right w-20">
              <div className="text-sm font-medium">{entry.accuracy.toFixed(1)}%</div>
              <div className="text-xs text-muted-foreground">Accuracy</div>
            </div>
          </div>
        );
      })}
    </div>
  );

  return (
    <div className="container mx-auto p-6 max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Trophy className="w-8 h-8 text-amber-500" />
            Leaderboard
          </h1>
          <p className="text-muted-foreground">See how you rank against other learners</p>
        </div>
      </div>

      {/* User's Rank Card */}
      <Card className="border-2 border-primary">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Your Ranking
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="text-3xl font-bold text-primary">#{userEntry.rank}</div>
            <Avatar className="h-12 w-12">
              <AvatarImage src={userEntry.avatar} />
              <AvatarFallback>{userEntry.username.charAt(0)}</AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <div className="font-medium">{userEntry.username}</div>
              <div className="text-sm text-muted-foreground">{userEntry.specialty}</div>
            </div>
            <div className="text-right">
              <div className="text-xl font-bold">Level {userEntry.level}</div>
              <div className="text-sm text-muted-foreground">{userEntry.xp} XP</div>
            </div>
            <div className="text-right">
              <div className="text-xl font-bold">{userEntry.accuracy.toFixed(1)}%</div>
              <div className="text-sm text-muted-foreground">Accuracy</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Leaderboard Tabs */}
      <Card>
        <CardHeader>
          <CardTitle>Global Rankings</CardTitle>
          <CardDescription>Filter by time period</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="all-time">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="all-time">All Time</TabsTrigger>
              <TabsTrigger value="monthly">This Month</TabsTrigger>
              <TabsTrigger value="weekly">This Week</TabsTrigger>
              <TabsTrigger value="daily">Today</TabsTrigger>
            </TabsList>
            <TabsContent value="all-time" className="mt-4">
              <LeaderboardTable entries={leaderboard.slice(0, 20)} />
            </TabsContent>
            <TabsContent value="monthly" className="mt-4">
              <LeaderboardTable entries={leaderboard.slice(0, 20)} />
            </TabsContent>
            <TabsContent value="weekly" className="mt-4">
              <LeaderboardTable entries={leaderboard.slice(0, 20)} />
            </TabsContent>
            <TabsContent value="daily" className="mt-4">
              <LeaderboardTable entries={leaderboard.slice(0, 20)} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Top 3 Spotlight */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Crown className="w-5 h-5 text-amber-500" />
            Top Performers
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {leaderboard.slice(0, 3).map((entry, index) => (
              <Card
                key={entry.rank}
                className={`${
                  index === 0
                    ? 'border-amber-500 bg-gradient-to-br from-amber-50 to-orange-50'
                    : index === 1
                    ? 'border-slate-400 bg-gradient-to-br from-slate-50 to-slate-100'
                    : 'border-amber-700 bg-gradient-to-br from-amber-100 to-orange-100'
                }`}
              >
                <CardContent className="pt-6 text-center">
                  <div className="mb-4">
                    {index === 0 && <Trophy className="w-12 h-12 text-amber-500 mx-auto" />}
                    {index === 1 && <Medal className="w-12 h-12 text-slate-400 mx-auto" />}
                    {index === 2 && <Medal className="w-12 h-12 text-amber-700 mx-auto" />}
                  </div>
                  <Avatar className="h-16 w-16 mx-auto mb-3">
                    <AvatarImage src={entry.avatar} />
                    <AvatarFallback>{entry.username.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <div className="font-bold text-lg">{entry.username}</div>
                  <div className="text-sm text-muted-foreground mb-2">{entry.specialty}</div>
                  <div className="text-2xl font-bold">Level {entry.level}</div>
                  <div className="text-sm text-muted-foreground">{entry.accuracy.toFixed(1)}% accuracy</div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
