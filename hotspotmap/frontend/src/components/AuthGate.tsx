import React from "react";

interface Props {
  children: React.ReactNode;
  onUnauthed: () => void;
}

const AuthGate: React.FC<Props> = ({ children, onUnauthed }) => {
  const token = localStorage.getItem("smartshield_token");
  if (!token) {
    onUnauthed();
    return null;
  }
  return <>{children}</>;
};

export default AuthGate;

