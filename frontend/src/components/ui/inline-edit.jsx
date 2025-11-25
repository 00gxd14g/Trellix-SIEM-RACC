import React, { useState } from 'react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Check, X, Edit3 } from 'lucide-react';

export function InlineEdit({ 
  value, 
  onSave, 
  type = 'text', 
  multiline = false, 
  className = '',
  placeholder = '',
  disabled = false
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value || '');
  const [isLoading, setIsLoading] = useState(false);

  const handleEdit = () => {
    if (disabled) return;
    setEditValue(value || '');
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (editValue === value) {
      setIsEditing(false);
      return;
    }
    
    setIsLoading(true);
    try {
      await onSave(editValue);
      setIsEditing(false);
    } catch (error) {
      console.error('Error saving value:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setEditValue(value || '');
    setIsEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !multiline && !e.shiftKey) {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  if (isEditing) {
    const InputComponent = multiline ? Textarea : Input;
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <InputComponent
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          type={type}
          placeholder={placeholder}
          className="flex-1"
          autoFocus
          disabled={isLoading}
        />
        <Button
          size="sm"
          variant="ghost"
          onClick={handleSave}
          disabled={isLoading}
          className="h-8 w-8 p-0 text-green-600 hover:text-green-700"
        >
          <Check className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleCancel}
          disabled={isLoading}
          className="h-8 w-8 p-0 text-red-600 hover:text-red-700"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <div 
      className={`group cursor-pointer flex items-center gap-2 hover:bg-muted/50 rounded px-2 py-1 ${disabled ? 'cursor-not-allowed opacity-50' : ''} ${className}`}
      onClick={handleEdit}
    >
      <span className="flex-1 break-words">
        {value || <span className="text-muted-foreground italic">{placeholder || 'Click to edit'}</span>}
      </span>
      {!disabled && (
        <Edit3 className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      )}
    </div>
  );
}

export function InlineSelect({ 
  value, 
  onSave, 
  options = [], 
  className = '',
  placeholder = 'Select...',
  disabled = false
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value || '');
  const [isLoading, setIsLoading] = useState(false);

  const handleEdit = () => {
    if (disabled) return;
    setEditValue(value || '');
    setIsEditing(true);
  };

  const handleSave = async () => {
    if (editValue === value) {
      setIsEditing(false);
      return;
    }
    
    setIsLoading(true);
    try {
      await onSave(editValue);
      setIsEditing(false);
    } catch (error) {
      console.error('Error saving value:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setEditValue(value || '');
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <select
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          className="flex-1 px-3 py-1 text-sm border border-input bg-background rounded-md"
          autoFocus
          disabled={isLoading}
        >
          <option value="">{placeholder}</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleSave}
          disabled={isLoading}
          className="h-8 w-8 p-0 text-green-600 hover:text-green-700"
        >
          <Check className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleCancel}
          disabled={isLoading}
          className="h-8 w-8 p-0 text-red-600 hover:text-red-700"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  const selectedOption = options.find(opt => opt.value === value);
  
  return (
    <div 
      className={`group cursor-pointer flex items-center gap-2 hover:bg-muted/50 rounded px-2 py-1 ${disabled ? 'cursor-not-allowed opacity-50' : ''} ${className}`}
      onClick={handleEdit}
    >
      <span className="flex-1">
        {selectedOption ? selectedOption.label : (value || <span className="text-muted-foreground italic">{placeholder}</span>)}
      </span>
      {!disabled && (
        <Edit3 className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
      )}
    </div>
  );
}