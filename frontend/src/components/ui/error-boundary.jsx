import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './card';
import logger from '@/lib/logger';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) { // eslint-disable-line no-unused-vars
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    logger.critical('React Error Boundary caught an error', {
      error: error.toString(),
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      props: this.props
    });
    
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null
    });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-background text-foreground p-4">
          <Card className="w-full max-w-md text-center">
            <CardHeader>
              <CardTitle className="text-destructive flex items-center justify-center gap-2">
                <AlertTriangle className="h-5 w-5" />
                Something went wrong.
              </CardTitle>
              <CardDescription>An unexpected error occurred in the application.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                We&apos;re sorry for the inconvenience. Please try refreshing the page.
              </p>
              <Button onClick={() => window.location.reload()} className="w-full">
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh Page
              </Button>
              {import.meta.env.DEV && this.state.errorInfo && (
                <details className="mt-4 text-left p-2 border rounded-md bg-muted/50 overflow-auto max-h-48">
                  <summary className="font-semibold cursor-pointer text-sm">Error Details</summary>
                  <pre className="mt-2 text-xs text-muted-foreground whitespace-pre-wrap break-all">
                    {this.state.error?.toString()}
                    <br />
                    {this.state.errorInfo?.componentStack}
                  </pre>
                </details>
              )}
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export { ErrorBoundary };
export default ErrorBoundary;
