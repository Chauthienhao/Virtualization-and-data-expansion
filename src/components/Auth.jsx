import React, { useState } from "react";
import { User, Mail, Lock } from "lucide-react";

export default function Auth({ initialMode, onSuccess, onSwitchMode }) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    onSuccess();
  };

  return (
    <div className="min-h-screen bg-white flex flex-col md:flex-row font-sans">
      <div className="w-full md:w-1/2 bg-[#38c8e6] text-white p-12 flex flex-col justify-center items-center text-center relative rounded-b-[100px] md:rounded-b-none md:rounded-r-[250px]">
        <div className="max-w-md space-y-4 z-10">
          <h2 className="text-3xl font-bold">
            {mode === "login" ? "New here ?" : "One of us?"}
          </h2>
          <p className="text-cyan-50">
            {mode === "login"
              ? "If you haven't signed up, What are you waiting for ?"
              : "If you have already signed up, that's great !! Please LOGIN"}
          </p>
          <button
            onClick={() => {
              const nextMode = mode === "login" ? "signup" : "login";
              setMode(nextMode);
              onSwitchMode(nextMode);
            }}
            className="mt-4 border-2 border-white text-white hover:bg-white hover:text-[#38c8e6] px-8 py-2.5 rounded-full font-semibold transition-all"
          >
            {mode === "login" ? "SIGN UP" : "LOGIN"}
          </button>
          <div className="pt-8 flex justify-center">
            <img
              src="https://illustrations.popsy.co/white/surveillance.svg"
              alt="Illustration"
              className="w-64 h-64 object-contain"
            />
          </div>
        </div>
      </div>

      <div className="w-full md:w-1/2 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md space-y-6">
          <h2 className="text-4xl font-bold text-gray-800 text-center mb-8">
            {mode === "login" ? "Sign in" : "Sign up"}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "signup" && (
              <div className="flex items-center bg-gray-100 rounded-full px-4 py-3">
                <User className="text-gray-400 w-5 h-5 mr-3" />
                <input
                  type="text"
                  placeholder="Name"
                  required
                  className="bg-transparent w-full outline-none text-gray-700"
                />
              </div>
            )}
            <div className="flex items-center bg-gray-100 rounded-full px-4 py-3">
              <Mail className="text-gray-400 w-5 h-5 mr-3" />
              <input
                type="email"
                placeholder="Email Address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="bg-transparent w-full outline-none text-gray-700"
              />
            </div>
            <div className="flex items-center bg-gray-100 rounded-full px-4 py-3">
              <Lock className="text-gray-400 w-5 h-5 mr-3" />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="bg-transparent w-full outline-none text-gray-700"
              />
            </div>
            {mode === "signup" && (
              <div className="flex items-center bg-gray-100 rounded-full px-4 py-3">
                <Lock className="text-gray-400 w-5 h-5 mr-3" />
                <input
                  type="password"
                  placeholder="Confirm Password"
                  required
                  className="bg-transparent w-full outline-none text-gray-700"
                />
              </div>
            )}
            <div className="text-center pt-4">
              <button
                type="submit"
                className="bg-[#38c8e6] text-white font-bold px-12 py-3 rounded-full hover:bg-cyan-600 transition-all shadow-md"
              >
                {mode === "login" ? "LOGIN" : "SIGN UP"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}