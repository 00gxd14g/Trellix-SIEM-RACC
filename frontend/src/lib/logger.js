// Frontend Logger Utility

const LogLevel = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
  CRITICAL: 4
};

class Logger {
  constructor() {
    this.logLevel = import.meta.env.DEV ? LogLevel.DEBUG : LogLevel.INFO;
    this.logs = [];
    this.maxLogs = 1000;
    this.enableConsole = true;
    this.enableRemote = import.meta.env.PROD;
    this.originalConsole = {
      log: console.log.bind(console),
      info: console.info.bind(console),
      warn: console.warn.bind(console),
      error: console.error.bind(console),
      debug: console.debug ? console.debug.bind(console) : console.log.bind(console)
    };
    
    // Setup global error handlers
    this.setupGlobalErrorHandlers();
  }

  setupGlobalErrorHandlers() {
    // Catch unhandled errors
    window.addEventListener('error', (event) => {
      this.error('Unhandled error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error?.stack || event.error
      });
    });

    // Catch unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.error('Unhandled promise rejection', {
        reason: event.reason,
        promise: event.promise
      });
    });

    // Intercept console errors
    const originalError = this.originalConsole.error;
    console.error = (...args) => {
      this.log(LogLevel.ERROR, 'Console error', { args }, { skipConsole: true });
      originalError(...args);
    };
  }

  getTimestamp() {
    return new Date().toISOString();
  }

  formatMessage(level, message, data) {
    return {
      timestamp: this.getTimestamp(),
      level: Object.keys(LogLevel).find(key => LogLevel[key] === level),
      message,
      data,
      userAgent: navigator.userAgent,
      url: window.location.href
    };
  }

  log(level, message, data = {}, options = {}) {
    if (level < this.logLevel) return;

    const logEntry = this.formatMessage(level, message, data);
    const { skipConsole = false, skipRemote = false, skipStore = false } = options;
    
    // Store in memory
    this.logs.push(logEntry);
    if (this.logs.length > this.maxLogs) {
      this.logs.shift();
    }

    // Console output
    if (this.enableConsole && !skipConsole) {
      const consoleMethod = this.getConsoleMethod(level);
      const color = this.getLogColor(level);
      const consoleFn = this.originalConsole[consoleMethod] || this.originalConsole.log;
      consoleFn(
        `%c[${logEntry.level}] ${logEntry.timestamp} - ${message}`,
        `color: ${color}; font-weight: bold;`,
        data
      );
    }

    // Send to remote server in production
    if (!skipRemote && this.enableRemote && level >= LogLevel.ERROR) {
      this.sendToRemote(logEntry);
    }

    // Store critical errors in localStorage
    if (!skipStore && level >= LogLevel.ERROR) {
      this.storeError(logEntry);
    }
  }

  getConsoleMethod(level) {
    switch (level) {
      case LogLevel.DEBUG: return 'debug';
      case LogLevel.INFO: return 'info';
      case LogLevel.WARN: return 'warn';
      case LogLevel.ERROR:
      case LogLevel.CRITICAL: return 'error';
      default: return 'log';
    }
  }

  getLogColor(level) {
    switch (level) {
      case LogLevel.DEBUG: return '#888';
      case LogLevel.INFO: return '#2196F3';
      case LogLevel.WARN: return '#FF9800';
      case LogLevel.ERROR: return '#F44336';
      case LogLevel.CRITICAL: return '#D32F2F';
      default: return '#000';
    }
  }

  storeError(logEntry) {
    try {
      const errors = JSON.parse(localStorage.getItem('app_errors') || '[]');
      errors.push(logEntry);
      // Keep only last 50 errors
      if (errors.length > 50) {
        errors.splice(0, errors.length - 50);
      }
      localStorage.setItem('app_errors', JSON.stringify(errors));
    } catch (e) {
      this.originalConsole.error('Failed to store error in localStorage', e);
    }
  }

  async sendToRemote(logEntry) {
    try {
      // Send log to backend API
      await fetch('/api/logs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(logEntry)
      });
    } catch (error) {
      // Silently fail - we don't want logging to break the app
      this.originalConsole.error('Failed to send log to remote server', error);
    }
  }

  // Public methods
  debug(message, data) {
    this.log(LogLevel.DEBUG, message, data);
  }

  info(message, data) {
    this.log(LogLevel.INFO, message, data);
  }

  warn(message, data) {
    this.log(LogLevel.WARN, message, data);
  }

  error(message, data) {
    this.log(LogLevel.ERROR, message, data);
  }

  critical(message, data) {
    this.log(LogLevel.CRITICAL, message, data);
  }

  // API call logging
  logApiCall(method, url, data, response, duration) {
    const logData = {
      method,
      url,
      requestData: data,
      response: response?.data,
      status: response?.status,
      duration: `${duration}ms`
    };

    if (response?.status >= 400) {
      this.error(`API Error: ${method} ${url}`, logData);
    } else {
      this.info(`API Call: ${method} ${url}`, logData);
    }
  }

  // Performance logging
  logPerformance(operation, duration) {
    const logData = {
      operation,
      duration: `${duration}ms`,
      timestamp: this.getTimestamp()
    };

    if (duration > 1000) {
      this.warn(`Slow operation: ${operation}`, logData);
    } else {
      this.debug(`Performance: ${operation}`, logData);
    }
  }

  // User action logging
  logUserAction(action, details = {}) {
    this.info(`User Action: ${action}`, {
      ...details,
      timestamp: this.getTimestamp()
    });
  }

  // Get all logs
  getLogs(level = null) {
    if (level === null) return this.logs;
    return this.logs.filter(log => LogLevel[log.level] >= level);
  }

  // Clear logs
  clearLogs() {
    this.logs = [];
    try {
      localStorage.removeItem('app_errors');
    } catch (e) {
      console.error('Failed to clear error logs', e);
    }
  }

  // Export logs
  exportLogs() {
    const blob = new Blob([JSON.stringify(this.logs, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `app-logs-${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
}

// Create singleton instance
const logger = new Logger();

// Export both the logger instance and the LogLevel enum
export { logger, LogLevel };
export default logger;
