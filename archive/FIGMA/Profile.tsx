import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { BadgeCard } from '../components/BadgeCard';
import { ProgressBar } from '../components/ProgressBar';
import { loadUserProgress, loadSubscription, getUsername, setUsername, getSpecialty, setSpecialty } from '../utils/storage';
import type { UserProgress, UserSubscription } from '../types';
import { User, Award, Settings, BarChart3, Crown } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

const ALL_BADGES = [
  { id: 'first_case', name: 'First Steps', description: 'Complete your first ABG case', icon: 'Footprints', rarity: 'common' as const },
  { id: 'case_10', name: 'Getting Started', description: 'Complete 10 ABG cases', icon: 'Zap', rarity: 'common' as const },
  { id: 'case_50', name: 'Dedicated Learner', description: 'Complete 50 ABG cases', icon: 'BookOpen', rarity: 'rare' as const },
  { id: 'case_100', name: 'ABG Expert', description: 'Complete 100 ABG cases', icon: 'Award', rarity: 'epic' as const },
  { id: 'streak_7', name: 'Week Warrior', description: 'Maintain a 7-day streak', icon: 'Flame', rarity: 'rare' as const },
  { id: 'streak_30', name: 'Month Master', description: 'Maintain a 30-day streak', icon: 'Trophy', rarity: 'legendary' as const },
  { id: 'accuracy_90', name: 'Precision Pro', description: 'Achieve 90% accuracy', icon: 'Target', rarity: 'epic' as const },
  { id: 'perfect_10', name: 'Perfect Ten', description: 'Get 10 cases correct in a row', icon: 'Star', rarity: 'rare' as const },
];

const SPECIALTIES = [
  'Medical Student',
  'Emergency Medicine',
  'Anesthesiology',
  'Critical Care',
  'Internal Medicine',
  'Respiratory Medicine',
  'Surgery',
  'Cardiology',
  'Pediatrics',
  'Other',
];

export function Profile() {
  const [progress, setProgress] = useState<UserProgress | null>(null);
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [localUsername, setLocalUsername] = useState('');
  const [localSpecialty, setLocalSpecialty] = useState('');

  useEffect(() => {
    setProgress(loadUserProgress());
    setSubscription(loadSubscription());
    setLocalUsername(getUsername());
    setLocalSpecialty(getSpecialty());
  }, []);

  const handleSave = () => {
    setUsername(localUsername);
    setSpecialty(localSpecialty);
    setEditMode(false);
  };

  if (!progress || !subscription) return null;

  const unlockedBadges = progress.badges;
  const lockedBadges = ALL_BADGES.filter(
    (badge) => !unlockedBadges.find((ub) => ub.id === badge.id)
  ).map((badge) => ({ ...badge, unlockedAt: '' }));

  return (
    <div className="container mx-auto p-6 max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <User className="w-8 h-8" />
          Profile
        </h1>
        {subscription.tier !== 'free' && (
          <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 text-white">
            <Crown className="w-4 h-4" />
            {subscription.tier === 'premium' ? 'Premium' : 'Pro'} Member
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Profile Info */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                User Info
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => (editMode ? handleSave() : setEditMode(true))}
                >
                  <Settings className="w-4 h-4" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {editMode ? (
                <>
                  <div className="space-y-2">
                    <Label>Username</Label>
                    <Input
                      value={localUsername}
                      onChange={(e) => setLocalUsername(e.target.value)}
                      placeholder="Enter username"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Specialty</Label>
                    <Select value={localSpecialty} onValueChange={setLocalSpecialty}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {SPECIALTIES.map((spec) => (
                          <SelectItem key={spec} value={spec}>
                            {spec}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Button onClick={handleSave} className="w-full">
                    Save Changes
                  </Button>
                </>
              ) : (
                <>
                  <div>
                    <div className="text-sm text-muted-foreground">Username</div>
                    <div className="text-lg font-medium">{localUsername}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Specialty</div>
                    <div className="text-lg font-medium">{localSpecialty}</div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5" />
                Statistics
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="text-sm text-muted-foreground">Level</div>
                <div className="text-3xl font-bold">{progress.level}</div>
              </div>
              <ProgressBar
                current={progress.xp}
                total={progress.xpToNextLevel}
                label="XP Progress"
              />
              <div className="grid grid-cols-2 gap-4 pt-4">
                <div>
                  <div className="text-sm text-muted-foreground">Cases</div>
                  <div className="text-2xl font-bold">{progress.completedCases}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Accuracy</div>
                  <div className="text-2xl font-bold">{progress.accuracy.toFixed(1)}%</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Streak</div>
                  <div className="text-2xl font-bold">{progress.currentStreak}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Best Streak</div>
                  <div className="text-2xl font-bold">{progress.longestStreak}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Badges */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Award className="w-5 h-5" />
                Achievements
              </CardTitle>
              <CardDescription>
                {unlockedBadges.length} of {ALL_BADGES.length} badges earned
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="unlocked">
                <TabsList className="grid w-full grid-cols-2 mb-4">
                  <TabsTrigger value="unlocked">
                    Unlocked ({unlockedBadges.length})
                  </TabsTrigger>
                  <TabsTrigger value="locked">
                    Locked ({lockedBadges.length})
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="unlocked">
                  {unlockedBadges.length > 0 ? (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {unlockedBadges.map((badge) => (
                        <BadgeCard key={badge.id} badge={badge} />
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      Complete cases to earn your first badge!
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="locked">
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {lockedBadges.map((badge) => (
                      <BadgeCard key={badge.id} badge={badge} locked={true} />
                    ))}
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
