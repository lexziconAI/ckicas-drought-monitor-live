import { useEffect, useCallback } from 'react';

interface ShortcutConfig {
  key: string;
  action: () => void;
  preventDefault?: boolean;
  description?: string;
}

/**
 * Custom hook for managing keyboard shortcuts
 * Automatically detects and prevents shortcuts when typing in input fields
 */
export const useKeyboardShortcuts = ({ shortcuts }: { shortcuts: ShortcutConfig[] }) => {
  const handleKeyPress = useCallback(
    (event: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in input fields, textareas, or contenteditable elements
      const target = event.target as HTMLElement;
      const isTyping =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      if (isTyping) {
        return;
      }

      // Find matching shortcut
      const shortcut = shortcuts.find((s) => s.key.toLowerCase() === event.key.toLowerCase());

      if (shortcut) {
        if (shortcut.preventDefault !== false) {
          event.preventDefault();
        }
        shortcut.action();
      }
    },
    [shortcuts]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyPress);

    return () => {
      window.removeEventListener('keydown', handleKeyPress);
    };
  }, [handleKeyPress]);
};
