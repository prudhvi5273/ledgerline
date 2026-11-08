import React, { useState, useRef, useEffect } from 'react';
import { Bot, X, Send, Sparkles, HelpCircle, Shield, ArrowRight, Minimize2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface Message {
  id: string;
  sender: 'ai' | 'user';
  text: string;
  timestamp: string;
}

export const AIChatbot: React.FC = () => {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'ai',
      text: `Hello ${user?.full_name || 'there'}! 👋 I am your **LedgerLine Financial & Architectural Assistant**.\n\nI can answer questions about double-entry accounting, concurrency safety, how our ledger guarantees money conservation, or help you navigate your accounts. How can I assist you today?`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const quickPrompts = [
    "How does double-entry work in LedgerLine?",
    "How does row locking prevent double-spending?",
    "What is an Idempotency-Key?",
    "Explain the Auditor reconciliation equation."
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const generateAIResponse = (query: string): string => {
    const q = query.toLowerCase();

    if (q.includes('double-entry') || q.includes('double entry') || q.includes('ledger')) {
      return `### Double-Entry Accounting in LedgerLine\n\nEvery financial transfer creates a **journal header** in \`ledger_transactions\` and exactly **two matching line items** in \`ledger_entries\`:\n\n1. **DEBIT Entry**: Deducted from the source account (\`balance_after = balance - amount\`).\n2. **CREDIT Entry**: Added to the destination account (\`balance_after = balance + amount\`).\n\n**System Invariant**: $\\sum \\text{Debits} = \\sum \\text{Credits}$ at all times. Money is never created or destroyed; it is only transferred between accounts. For external deposits and withdrawals, entries are balanced against the internal \`SYSTEM_CLEARING\` account!`;
    }

    if (q.includes('row lock') || q.includes('lock') || q.includes('race') || q.includes('concurrency') || q.includes('deadlock') || q.includes('overdraft')) {
      return `### Concurrency & Deadlock Prevention\n\nLedgerLine uses PostgreSQL row-level locks (\`SELECT ... FOR UPDATE\`) with **Deterministic Lock Ordering**:\n\n- When transferring between Account A and Account B, locks are acquired in strictly **ascending UUID order**: \`ORDER BY id ASC\`.\n- Because all concurrent transactions lock \`min(A, B)\` first and \`max(A, B)\` second, circular wait deadlocks are mathematically impossible!\n- Non-negative balances (\`CHECK (balance >= 0)\`) are verified inside the locked transaction, so simultaneous withdrawal races (e.g. two ₹800 requests against a ₹1,000 balance) allow exactly one to succeed and cleanly reject the second!`;
    }

    if (q.includes('idempotency') || q.includes('duplicate') || q.includes('retry')) {
      return `### Exact-Once Idempotency\n\nEvery money-moving endpoint requires an **\`Idempotency-Key\`** header (UUID v4):\n\n1. The server hashes the request payload (SHA-256) and stores it in \`idempotency_records\` with status \`PENDING\`.\n2. If the user double-clicks or a network retry arrives with the **same key and same payload**, the server immediately replays the cached 201 Created response **without creating another transaction**.\n3. If the same key is reused with a **different payload**, the server immediately rejects it with **HTTP 409 Conflict**!`;
    }

    if (q.includes('auditor') || q.includes('reconciliation') || q.includes('balance')) {
      return `### Auditor Reconciliation & Invariant Check\n\nThe **Auditor Portal** runs an independent real-time verification query across the entire database:\n\n- **Formula**: $\\sum \\text{All Debits} - \\sum \\text{All Credits} = 0.0000$\n- **Conservation**: $\\text{User Balances} + \\text{System Clearing Balance} = 0.0000$\n\nIf the discrepancy is ₹0.0000, the ledger is mathematically **PROVEN & BALANCED**. Furthermore, Auditors have strict read-only permissions enforced by backend RBAC guards!`;
    }

    if (q.includes('role') || q.includes('admin') || q.includes('permission')) {
      return `### Role-Based Access Control (RBAC)\n\nLedgerLine implements 3 distinct roles:\n\n- **Account Holder**: Manages own accounts, initiates idempotent transfers, views personal statements.\n- **Administrator**: Views all accounts and users, provisions privileged users (\`POST /api/v1/admin/users\`), freezes/unfreezes accounts, inspects system audit logs.\n- **Auditor**: Independent read-only financial compliance examiner. Cannot deposit, withdraw, transfer, or modify records.`;
    }

    return `Thank you for your question! LedgerLine enforces strict financial integrity:\n\n- **Double-Entry**: Every transfer balances Debits and Credits.\n- **Concurrency**: Deterministic \`SELECT FOR UPDATE\` row locks prevent overdrafts and deadlocks.\n- **Idempotency**: Duplicate payment requests return cached results safely.\n- **Auditability**: All actions and refused attempts are permanently logged.\n\nYou can explore your accounts under **My Accounts** or verify the global balance in the **Auditor Portal**!`;
  };

  const handleSend = (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    setTimeout(() => {
      const responseText = generateAIResponse(query);
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: responseText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, aiMsg]);
      setIsTyping(false);
    }, 500);
  };

  return (
    <div className="fixed bottom-5 right-5 z-40 print:hidden">
      {!isOpen ? (
        /* Floating Launcher Button */
        <button
          onClick={() => setIsOpen(true)}
          className="group relative flex items-center gap-2.5 px-4 py-3 rounded-full bg-gradient-to-r from-emerald-600 to-teal-500 text-white font-semibold text-xs shadow-xl shadow-emerald-600/30 hover:shadow-emerald-500/50 hover:scale-105 transition-all duration-200 border border-emerald-400/30"
        >
          <div className="relative">
            <Bot size={18} />
            <span className="absolute -top-1 -right-1 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-200 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-white"></span>
            </span>
          </div>
          <span>LedgerLine AI Assistant</span>
          <Sparkles size={14} className="text-emerald-200 animate-pulse" />
        </button>
      ) : (
        /* Expanded Chat Window */
        <div className="w-96 sm:w-[420px] h-[540px] rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-5 duration-200">
          {/* Header */}
          <div className="p-3.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                <Bot size={18} />
              </div>
              <div>
                <h3 className="font-bold text-slate-100 text-xs flex items-center gap-1.5">
                  LedgerLine AI Assistant
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.2 rounded border border-emerald-500/30 font-mono">
                    ONLINE
                  </span>
                </h3>
                <p className="text-[10px] text-slate-400">Financial Integrity & Architecture Bot</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          {/* Messages Stream */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3.5 text-xs bg-slate-900/40">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl p-3 leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-emerald-600 text-white rounded-br-none shadow-md shadow-emerald-600/10'
                      : 'bg-slate-950 border border-slate-800 text-slate-200 rounded-bl-none'
                  }`}
                >
                  <div className="whitespace-pre-line text-xs font-sans">
                    {msg.text}
                  </div>
                </div>
                <span className="text-[9px] text-slate-400 font-mono mt-1 px-1">{msg.timestamp}</span>
              </div>
            ))}

            {isTyping && (
              <div className="flex items-center gap-1.5 p-3 rounded-2xl bg-slate-950 border border-slate-800 text-slate-400 text-xs w-24">
                <span className="animate-bounce">●</span>
                <span className="animate-bounce [animation-delay:0.2s]">●</span>
                <span className="animate-bounce [animation-delay:0.4s]">●</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompts */}
          <div className="px-3 py-2 bg-slate-950 border-t border-slate-800/80 flex gap-1.5 overflow-x-auto no-scrollbar">
            {quickPrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => handleSend(prompt)}
                className="whitespace-nowrap px-2.5 py-1 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[10px] text-slate-400 hover:text-emerald-300 transition-colors shrink-0"
              >
                {prompt}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="p-2.5 bg-slate-950 border-t border-slate-800 flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about LedgerLine..."
              className="flex-1 px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500 placeholder-slate-400"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="p-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white transition-colors"
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
};
