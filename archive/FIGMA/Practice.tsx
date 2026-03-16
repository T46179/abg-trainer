import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { ABGDisplay } from '../components/ABGDisplay';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Label } from '../components/ui/label';
import { Alert, AlertDescription } from '../components/ui/alert';
import { generateABGCase } from '../utils/abg-generator';
import {
  loadUserProgress,
  loadSubscription,
  addXP,
  recordCaseCompletion,
  updateStreak,
  decrementDailyCases,
} from '../utils/storage';
import type { ABGCase, DifficultyLevel, UserProgress, UserSubscription } from '../types';
import { CheckCircle2, XCircle, Lightbulb, RotateCcw, ArrowRight } from 'lucide-react';
import confetti from 'canvas-confetti';

export function Practice() {
  const navigate = useNavigate();
  const [progress, setProgress] = useState<UserProgress | null>(null);
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [difficulty, setDifficulty] = useState<DifficultyLevel>('beginner');
  const [currentCase, setCurrentCase] = useState<ABGCase | null>(null);
  const [userAnswer, setUserAnswer] = useState({
    primaryDisorder: '',
    compensation: '',
    oxygenation: '',
  });
  const [showResult, setShowResult] = useState(false);
  const [isCorrect, setIsCorrect] = useState(false);

  useEffect(() => {
    const loadedProgress = loadUserProgress();
    const loadedSubscription = loadSubscription();
    setProgress(loadedProgress);
    setSubscription(loadedSubscription);

    // Set initial difficulty based on unlocked levels
    if (loadedProgress.unlockedDifficulties.includes('advanced')) {
      setDifficulty('advanced');
    } else if (loadedProgress.unlockedDifficulties.includes('intermediate')) {
      setDifficulty('intermediate');
    } else {
      setDifficulty('beginner');
    }
  }, []);

  const generateNewCase = () => {
    if (!progress || !subscription) return;

    // Check if user has cases remaining
    if (subscription.tier !== 'pro' && subscription.casesRemainingToday <= 0) {
      navigate('/upgrade');
      return;
    }

    const newCase = generateABGCase(difficulty);
    setCurrentCase(newCase);
    setUserAnswer({ primaryDisorder: '', compensation: '', oxygenation: '' });
    setShowResult(false);
  };

  useEffect(() => {
    if (progress && subscription) {
      generateNewCase();
    }
  }, [progress, subscription]);

  const handleSubmit = () => {
    if (!currentCase || !userAnswer.primaryDisorder || !userAnswer.oxygenation) {
      return;
    }

    // Simple matching logic
    const disorderMatch = currentCase.disorder.includes(userAnswer.primaryDisorder.toLowerCase().replace(' ', '_'));
    const oxygenationCorrect =
      (currentCase.values.PaO2 < 80 && userAnswer.oxygenation === 'hypoxemia') ||
      (currentCase.values.PaO2 >= 80 && userAnswer.oxygenation === 'normal');

    const correct = disorderMatch && oxygenationCorrect;
    setIsCorrect(correct);
    setShowResult(true);

    // Update progress
    updateStreak();
    recordCaseCompletion(correct);
    decrementDailyCases();

    if (correct) {
      const xpGain = difficulty === 'beginner' ? 10 : difficulty === 'intermediate' ? 20 : difficulty === 'advanced' ? 30 : 50;
      const result = addXP(xpGain);

      if (result.leveledUp) {
        confetti({
          particleCount: 100,
          spread: 70,
          origin: { y: 0.6 },
        });
      }
    }

    // Reload progress and subscription
    setProgress(loadUserProgress());
    setSubscription(loadSubscription());
  };

  const handleNextCase = () => {
    generateNewCase();
  };

  if (!currentCase || !progress || !subscription) {
    return (
      <div className="container mx-auto p-6 max-w-4xl">
        <Card>
          <CardContent className="py-12 text-center">
            <div className="text-lg">Loading...</div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Practice Mode</h1>
          <p className="text-muted-foreground">
            Level {progress.level} • {progress.xp} / {progress.xpToNextLevel} XP
          </p>
        </div>
        <div className="text-right">
          <div className="text-sm text-muted-foreground">Difficulty</div>
          <Select
            value={difficulty}
            onValueChange={(value) => {
              setDifficulty(value as DifficultyLevel);
              setTimeout(generateNewCase, 100);
            }}
            disabled={showResult}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {progress.unlockedDifficulties.map((diff) => {
                const locked = diff === 'master' && !subscription.hasAccessToMaster;
                return (
                  <SelectItem key={diff} value={diff} disabled={locked}>
                    {diff.charAt(0).toUpperCase() + diff.slice(1)}
                    {locked && ' 🔒'}
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Cases remaining */}
      {subscription.tier !== 'pro' && (
        <Alert>
          <AlertDescription>
            {subscription.casesRemainingToday} case{subscription.casesRemainingToday !== 1 ? 's' : ''} remaining today
          </AlertDescription>
        </Alert>
      )}

      {/* Clinical Scenario */}
      <Card>
        <CardHeader>
          <CardTitle>Clinical Scenario</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-lg">{currentCase.clinicalScenario}</p>
        </CardContent>
      </Card>

      {/* ABG Values */}
      <ABGDisplay values={currentCase.values} showNormalRanges={true} />

      {/* Answer Form */}
      {!showResult ? (
        <Card>
          <CardHeader>
            <CardTitle>Interpret the ABG</CardTitle>
            <CardDescription>Select your interpretation based on the values</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Primary Disorder</Label>
              <Select value={userAnswer.primaryDisorder} onValueChange={(value) => setUserAnswer({ ...userAnswer, primaryDisorder: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select primary disorder" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="respiratory acidosis">Respiratory Acidosis</SelectItem>
                  <SelectItem value="respiratory alkalosis">Respiratory Alkalosis</SelectItem>
                  <SelectItem value="metabolic acidosis">Metabolic Acidosis</SelectItem>
                  <SelectItem value="metabolic alkalosis">Metabolic Alkalosis</SelectItem>
                  <SelectItem value="mixed disorder">Mixed Disorder</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Compensation Status</Label>
              <Select value={userAnswer.compensation} onValueChange={(value) => setUserAnswer({ ...userAnswer, compensation: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select compensation status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="uncompensated">Uncompensated</SelectItem>
                  <SelectItem value="partially compensated">Partially Compensated</SelectItem>
                  <SelectItem value="fully compensated">Fully Compensated</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Oxygenation Status</Label>
              <Select value={userAnswer.oxygenation} onValueChange={(value) => setUserAnswer({ ...userAnswer, oxygenation: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select oxygenation status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="hypoxemia">Hypoxemia</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              onClick={handleSubmit}
              className="w-full"
              disabled={!userAnswer.primaryDisorder || !userAnswer.oxygenation}
            >
              Submit Answer
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card className={isCorrect ? 'border-green-500 bg-green-50/50' : 'border-red-500 bg-red-50/50'}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {isCorrect ? (
                <>
                  <CheckCircle2 className="w-6 h-6 text-green-600" />
                  Correct!
                </>
              ) : (
                <>
                  <XCircle className="w-6 h-6 text-red-600" />
                  Incorrect
                </>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-2">
              <Lightbulb className="w-5 h-5 text-amber-500 mt-1 flex-shrink-0" />
              <div>
                <div className="font-medium mb-2">Explanation:</div>
                <p className="text-sm">{currentCase.explanation}</p>
              </div>
            </div>

            {isCorrect && (
              <div className="text-sm text-green-700">
                +{difficulty === 'beginner' ? 10 : difficulty === 'intermediate' ? 20 : difficulty === 'advanced' ? 30 : 50} XP earned!
              </div>
            )}

            <div className="flex gap-3">
              <Button onClick={handleNextCase} className="flex-1">
                <ArrowRight className="w-4 h-4 mr-2" />
                Next Case
              </Button>
              <Button onClick={() => navigate('/dashboard')} variant="outline">
                Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
