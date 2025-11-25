const clampSeverity = (input) => {
  const numeric = Number.parseInt(input, 10);
  if (Number.isNaN(numeric)) {
    return 0;
  }
  return Math.min(100, Math.max(0, numeric));
};

export const getSeverityMeta = (input) => {
  const severity = clampSeverity(input);

  if (severity >= 80) {
    return {
      variant: 'destructive',
      label: 'Critical',
      barClass: 'bg-red-500',
      value: severity,
    };
  }

  if (severity >= 60) {
    return {
      variant: 'warning',
      label: 'High',
      barClass: 'bg-orange-500',
      value: severity,
    };
  }

  if (severity >= 40) {
    return {
      variant: 'default',
      label: 'Medium',
      barClass: 'bg-yellow-500',
      value: severity,
    };
  }

  return {
    variant: 'secondary',
    label: 'Low',
    barClass: 'bg-green-500',
    value: severity,
  };
};
