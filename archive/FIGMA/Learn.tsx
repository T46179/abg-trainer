import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { ABGDisplay } from '../components/ABGDisplay';
import { Alert, AlertDescription } from '../components/ui/alert';
import { generateABGCase } from '../utils/abg-generator';
import { loadUserProgress, loadSubscription, decrementDailyCases } from '../utils/storage';
import type { ABGCase, DifficultyLevel, UserProgress, UserSubscription } from '../types';
import { BookOpen, ArrowRight, CheckCircle, Lightbulb } from 'lucide-react';

const lessons = [
  {
    id: 1,
    title: 'Introduction to ABG',
    description: 'Learn the basics of arterial blood gas interpretation',
    difficulty: 'beginner' as DifficultyLevel,
    content: `
      <h3>What is an Arterial Blood Gas?</h3>
      <p>An Arterial Blood Gas (ABG) is a blood test that measures:</p>
      <ul>
        <li><strong>pH:</strong> Measures acidity/alkalinity (Normal: 7.35-7.45)</li>
        <li><strong>PaCO₂:</strong> Partial pressure of carbon dioxide (Normal: 35-45 mmHg)</li>
        <li><strong>HCO₃⁻:</strong> Bicarbonate level (Normal: 22-26 mEq/L)</li>
        <li><strong>PaO₂:</strong> Partial pressure of oxygen (Normal: 80-100 mmHg)</li>
        <li><strong>Base Excess:</strong> Excess or deficit of base (Normal: -2 to +2 mEq/L)</li>
      </ul>
      <p>These values help diagnose respiratory and metabolic disorders.</p>
    `,
  },
  {
    id: 2,
    title: 'Step-by-Step Interpretation',
    description: 'Master the systematic approach to ABG analysis',
    difficulty: 'beginner' as DifficultyLevel,
    content: `
      <h3>The 5-Step Approach</h3>
      <ol>
        <li><strong>Check the pH:</strong> Is it acidotic (<7.35) or alkalotic (>7.45)?</li>
        <li><strong>Determine respiratory involvement:</strong> Look at PaCO₂
          <ul>
            <li>High PaCO₂ (>45) = Respiratory acidosis</li>
            <li>Low PaCO₂ (<35) = Respiratory alkalosis</li>
          </ul>
        </li>
        <li><strong>Determine metabolic involvement:</strong> Look at HCO₃⁻
          <ul>
            <li>High HCO₃⁻ (>26) = Metabolic alkalosis</li>
            <li>Low HCO₃⁻ (<22) = Metabolic acidosis</li>
          </ul>
        </li>
        <li><strong>Identify the primary disorder:</strong> Which change matches the pH direction?</li>
        <li><strong>Check for compensation:</strong> Is the other system trying to normalize pH?</li>
      </ol>
    `,
  },
  {
    id: 3,
    title: 'Respiratory Disorders',
    description: 'Understanding respiratory acidosis and alkalosis',
    difficulty: 'intermediate' as DifficultyLevel,
    content: `
      <h3>Respiratory Acidosis</h3>
      <p><strong>Cause:</strong> Hypoventilation leading to CO₂ retention</p>
      <p><strong>Pattern:</strong> ↓pH, ↑PaCO₂</p>
      <p><strong>Common causes:</strong> COPD, asthma, respiratory depression</p>
      
      <h3>Respiratory Alkalosis</h3>
      <p><strong>Cause:</strong> Hyperventilation leading to CO₂ loss</p>
      <p><strong>Pattern:</strong> ↑pH, ↓PaCO₂</p>
      <p><strong>Common causes:</strong> Anxiety, sepsis, high altitude</p>
    `,
  },
  {
    id: 4,
    title: 'Metabolic Disorders',
    description: 'Understanding metabolic acidosis and alkalosis',
    difficulty: 'intermediate' as DifficultyLevel,
    content: `
      <h3>Metabolic Acidosis</h3>
      <p><strong>Cause:</strong> Loss of bicarbonate or gain of acid</p>
      <p><strong>Pattern:</strong> ↓pH, ↓HCO₃⁻</p>
      <p><strong>Common causes:</strong> DKA, renal failure, diarrhea, lactic acidosis</p>
      
      <h3>Metabolic Alkalosis</h3>
      <p><strong>Cause:</strong> Loss of acid or gain of bicarbonate</p>
      <p><strong>Pattern:</strong> ↑pH, ↑HCO₃⁻</p>
      <p><strong>Common causes:</strong> Vomiting, diuretics, hyperaldosteronism</p>
    `,
  },
  {
    id: 5,
    title: 'Compensation',
    description: 'Learn how the body compensates for pH imbalances',
    difficulty: 'advanced' as DifficultyLevel,
    content: `
      <h3>Understanding Compensation</h3>
      <p>The body attempts to normalize pH through compensatory mechanisms:</p>
      
      <h4>Respiratory Compensation (for metabolic disorders)</h4>
      <ul>
        <li>Fast (minutes to hours)</li>
        <li>Adjusts ventilation to change CO₂</li>
      </ul>
      
      <h4>Metabolic Compensation (for respiratory disorders)</h4>
      <ul>
        <li>Slow (hours to days)</li>
        <li>Kidneys adjust HCO₃⁻ retention/excretion</li>
      </ul>
      
      <h4>Types of Compensation</h4>
      <ul>
        <li><strong>Uncompensated:</strong> Only primary disorder present</li>
        <li><strong>Partially Compensated:</strong> Both systems abnormal, pH still abnormal</li>
        <li><strong>Fully Compensated:</strong> Both systems abnormal, pH normalized</li>
      </ul>
    `,
  },
];

export function Learn() {
  const navigate = useNavigate();
  const [progress, setProgress] = useState<UserProgress | null>(null);
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [currentLesson, setCurrentLesson] = useState(0);
  const [showExample, setShowExample] = useState(false);
  const [exampleCase, setExampleCase] = useState<ABGCase | null>(null);

  useEffect(() => {
    setProgress(loadUserProgress());
    setSubscription(loadSubscription());
  }, []);

  const handleShowExample = () => {
    if (!subscription) return;
    
    if (subscription.tier !== 'pro' && subscription.casesRemainingToday <= 0) {
      navigate('/upgrade');
      return;
    }

    const example = generateABGCase(lessons[currentLesson].difficulty);
    setExampleCase(example);
    setShowExample(true);
    decrementDailyCases();
    setSubscription(loadSubscription());
  };

  const handleNextLesson = () => {
    if (currentLesson < lessons.length - 1) {
      setCurrentLesson(currentLesson + 1);
      setShowExample(false);
      setExampleCase(null);
    }
  };

  const handlePreviousLesson = () => {
    if (currentLesson > 0) {
      setCurrentLesson(currentLesson - 1);
      setShowExample(false);
      setExampleCase(null);
    }
  };

  const lesson = lessons[currentLesson];

  if (!progress || !subscription) return null;

  return (
    <div className="container mx-auto p-6 max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <BookOpen className="w-8 h-8" />
            Learn ABG Interpretation
          </h1>
          <p className="text-muted-foreground">
            Lesson {currentLesson + 1} of {lessons.length}
          </p>
        </div>
      </div>

      {/* Progress Indicator */}
      <div className="flex gap-2">
        {lessons.map((_, index) => (
          <div
            key={index}
            className={`h-2 flex-1 rounded-full ${
              index === currentLesson
                ? 'bg-primary'
                : index < currentLesson
                ? 'bg-primary/50'
                : 'bg-muted'
            }`}
          />
        ))}
      </div>

      {/* Lesson Content */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{lesson.title}</CardTitle>
              <CardDescription>{lesson.description}</CardDescription>
            </div>
            <div className="px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium">
              {lesson.difficulty.charAt(0).toUpperCase() + lesson.difficulty.slice(1)}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div
            className="prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: lesson.content }}
          />
        </CardContent>
      </Card>

      {/* Example Section */}
      {!showExample ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-amber-500" />
              Practice Example
            </CardTitle>
            <CardDescription>
              See a real example to reinforce your learning
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleShowExample} className="w-full">
              Generate Practice Example
            </Button>
            {subscription.tier !== 'pro' && (
              <div className="text-sm text-muted-foreground text-center mt-3">
                {subscription.casesRemainingToday} case{subscription.casesRemainingToday !== 1 ? 's' : ''} remaining today
              </div>
            )}
          </CardContent>
        </Card>
      ) : exampleCase ? (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Clinical Scenario</CardTitle>
            </CardHeader>
            <CardContent>
              <p>{exampleCase.clinicalScenario}</p>
            </CardContent>
          </Card>

          <ABGDisplay values={exampleCase.values} showNormalRanges={true} />

          <Card className="border-green-500 bg-green-50/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                Interpretation
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div>
                  <strong>Disorder:</strong>{' '}
                  {exampleCase.disorder.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                </div>
                <div>
                  <strong>Explanation:</strong>
                  <p className="mt-1 text-sm">{exampleCase.explanation}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Button onClick={() => setShowExample(false)} variant="outline" className="w-full">
            Hide Example
          </Button>
        </div>
      ) : null}

      {/* Navigation */}
      <div className="flex justify-between gap-4">
        <Button
          onClick={handlePreviousLesson}
          variant="outline"
          disabled={currentLesson === 0}
          className="flex-1"
        >
          Previous Lesson
        </Button>
        <Button
          onClick={() => navigate('/practice')}
          variant="outline"
          className="flex-1"
        >
          Practice Now
        </Button>
        <Button
          onClick={handleNextLesson}
          disabled={currentLesson === lessons.length - 1}
          className="flex-1"
        >
          Next Lesson
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
}
