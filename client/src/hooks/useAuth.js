import { useContext } from "react";
import { AuthContext } from "../context/authStore";

export const useAuth = () => useContext(AuthContext);
