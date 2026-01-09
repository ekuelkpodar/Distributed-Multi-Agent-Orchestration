import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Settings,
  Palette,
  Bell,
  Shield,
  Database,
  Server,
  Save,
  RotateCcw,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export default function SettingsPage() {
  const [theme, setTheme] = useState('dark');
  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [wsUrl, setWsUrl] = useState('ws://localhost:8000');
  const [refreshInterval, setRefreshInterval] = useState('5000');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [soundEnabled, setSoundEnabled] = useState(false);

  const handleSave = () => {
    // In a real app, this would save to localStorage or a backend
    alert('Settings saved!');
  };

  const handleReset = () => {
    setTheme('dark');
    setApiUrl('http://localhost:8000');
    setWsUrl('ws://localhost:8000');
    setRefreshInterval('5000');
    setNotificationsEnabled(true);
    setSoundEnabled(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">
            Configure your dashboard preferences and connections
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" onClick={handleReset}>
            <RotateCcw className="mr-2 h-4 w-4" />
            Reset
          </Button>
          <Button onClick={handleSave}>
            <Save className="mr-2 h-4 w-4" />
            Save Changes
          </Button>
        </div>
      </div>

      {/* Settings Tabs */}
      <Tabs defaultValue="general" className="space-y-6">
        <TabsList>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="connections">Connections</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="about">About</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-6">
          {/* Appearance */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Palette className="h-5 w-5 text-primary" />
                Appearance
              </CardTitle>
              <CardDescription>
                Customize the look and feel of your dashboard
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <label className="text-sm font-medium">Theme</label>
                <Select value={theme} onValueChange={setTheme}>
                  <SelectTrigger className="w-[200px] bg-background">
                    <SelectValue placeholder="Select theme" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dark">Dark</SelectItem>
                    <SelectItem value="light">Light</SelectItem>
                    <SelectItem value="system">System</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Choose your preferred color scheme
                </p>
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium">Data Refresh Interval</label>
                <Select value={refreshInterval} onValueChange={setRefreshInterval}>
                  <SelectTrigger className="w-[200px] bg-background">
                    <SelectValue placeholder="Select interval" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1000">1 second</SelectItem>
                    <SelectItem value="3000">3 seconds</SelectItem>
                    <SelectItem value="5000">5 seconds</SelectItem>
                    <SelectItem value="10000">10 seconds</SelectItem>
                    <SelectItem value="30000">30 seconds</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  How often to fetch updated data from the API
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="connections" className="space-y-6">
          {/* API Configuration */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Server className="h-5 w-5 text-primary" />
                API Connection
              </CardTitle>
              <CardDescription>
                Configure the connection to the backend API
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <label className="text-sm font-medium">API Base URL</label>
                <Input
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  placeholder="http://localhost:8000"
                  className="bg-background"
                />
                <p className="text-xs text-muted-foreground">
                  The base URL for the orchestrator API
                </p>
              </div>

              <div className="grid gap-2">
                <label className="text-sm font-medium">WebSocket URL</label>
                <Input
                  value={wsUrl}
                  onChange={(e) => setWsUrl(e.target.value)}
                  placeholder="ws://localhost:8000"
                  className="bg-background"
                />
                <p className="text-xs text-muted-foreground">
                  The WebSocket URL for real-time updates
                </p>
              </div>

              <div className="flex items-center gap-2 pt-2">
                <Button variant="outline" size="sm">
                  Test Connection
                </Button>
                <Badge variant="outline" className="border-green-500/50 text-green-400">
                  Connected
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Database Info */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Database className="h-5 w-5 text-primary" />
                Database Configuration
              </CardTitle>
              <CardDescription>
                Database connection information (read-only)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg bg-background/50 p-3">
                  <p className="text-xs text-muted-foreground">Type</p>
                  <p className="font-medium">PostgreSQL</p>
                </div>
                <div className="rounded-lg bg-background/50 p-3">
                  <p className="text-xs text-muted-foreground">Status</p>
                  <Badge variant="outline" className="border-green-500/50 text-green-400">
                    Connected
                  </Badge>
                </div>
                <div className="rounded-lg bg-background/50 p-3">
                  <p className="text-xs text-muted-foreground">Cache</p>
                  <p className="font-medium">Redis</p>
                </div>
                <div className="rounded-lg bg-background/50 p-3">
                  <p className="text-xs text-muted-foreground">Message Queue</p>
                  <p className="font-medium">Apache Kafka</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications" className="space-y-6">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Bell className="h-5 w-5 text-primary" />
                Notification Preferences
              </CardTitle>
              <CardDescription>
                Configure how you receive notifications
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between rounded-lg border border-border/50 p-4">
                <div>
                  <p className="font-medium">Enable Notifications</p>
                  <p className="text-sm text-muted-foreground">
                    Show desktop notifications for important events
                  </p>
                </div>
                <Button
                  variant={notificationsEnabled ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setNotificationsEnabled(!notificationsEnabled)}
                >
                  {notificationsEnabled ? 'Enabled' : 'Disabled'}
                </Button>
              </div>

              <div className="flex items-center justify-between rounded-lg border border-border/50 p-4">
                <div>
                  <p className="font-medium">Sound Alerts</p>
                  <p className="text-sm text-muted-foreground">
                    Play sounds for task completion and errors
                  </p>
                </div>
                <Button
                  variant={soundEnabled ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSoundEnabled(!soundEnabled)}
                >
                  {soundEnabled ? 'Enabled' : 'Disabled'}
                </Button>
              </div>

              <div className="pt-4">
                <p className="text-sm font-medium mb-3">Notify me about:</p>
                <div className="space-y-2">
                  {['Task completed', 'Task failed', 'Agent offline', 'System alerts'].map((item) => (
                    <label key={item} className="flex items-center gap-2">
                      <input type="checkbox" defaultChecked className="rounded" />
                      <span className="text-sm">{item}</span>
                    </label>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="about" className="space-y-6">
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Settings className="h-5 w-5 text-primary" />
                About
              </CardTitle>
              <CardDescription>
                Information about this application
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center py-6">
                <div className="flex items-center justify-center gap-2 mb-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500 to-cyan-500">
                    <Settings className="h-8 w-8 text-white" />
                  </div>
                </div>
                <h2 className="text-2xl font-bold">Multi-Agent Orchestration Platform</h2>
                <p className="text-muted-foreground mt-1">Version 1.0.0</p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg bg-background/50 p-4">
                  <p className="text-sm text-muted-foreground">Frontend</p>
                  <p className="font-medium">React 18 + TypeScript + Vite</p>
                </div>
                <div className="rounded-lg bg-background/50 p-4">
                  <p className="text-sm text-muted-foreground">Backend</p>
                  <p className="font-medium">Python + FastAPI</p>
                </div>
                <div className="rounded-lg bg-background/50 p-4">
                  <p className="text-sm text-muted-foreground">Database</p>
                  <p className="font-medium">PostgreSQL + Redis</p>
                </div>
                <div className="rounded-lg bg-background/50 p-4">
                  <p className="text-sm text-muted-foreground">Message Queue</p>
                  <p className="font-medium">Apache Kafka</p>
                </div>
              </div>

              <div className="rounded-lg border border-border/50 p-4">
                <p className="text-sm font-medium mb-2">Technologies Used</p>
                <div className="flex flex-wrap gap-2">
                  {[
                    'React',
                    'TypeScript',
                    'Tailwind CSS',
                    'shadcn/ui',
                    'TanStack Query',
                    'Zustand',
                    'Recharts',
                    'Framer Motion',
                    'Socket.IO',
                  ].map((tech) => (
                    <Badge key={tech} variant="secondary">
                      {tech}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Security Info */}
          <Card className="border-border/50 bg-card/50 backdrop-blur">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Shield className="h-5 w-5 text-primary" />
                Security
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">API Authentication</span>
                  <Badge variant="outline" className="border-green-500/50 text-green-400">
                    Active
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">HTTPS</span>
                  <Badge variant="outline" className="border-yellow-500/50 text-yellow-400">
                    Development Mode
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">CORS</span>
                  <Badge variant="outline" className="border-green-500/50 text-green-400">
                    Configured
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}
