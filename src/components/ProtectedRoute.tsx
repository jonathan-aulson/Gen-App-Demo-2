import React from "react";
import { Navigate } from "react-router-dom";
import { useAppSelector } from "../store/hooks";

interface Props {
  children: JSX.Element;
}

const ProtectedRoute: React.FC<Props> = ({ children }) => {
  const user = useAppSelector((state) => state.user);
  const token = localStorage.getItem("token");

  if (!user.token && !token) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default ProtectedRoute;