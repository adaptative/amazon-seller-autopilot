import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
}

export function Button({ variant = 'primary', className = '', ...props }: ButtonProps) {
  return <button className={`btn btn-${variant} ${className}`} {...props} />;
}
