import { LibraryBig } from "lucide-react";
import React from "react";

function Sidebar(){
    return (
        <div className="transition duration-300 ease-in-out bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border-r border-slate-200/50 dark:border-slate-700/50 flex flex-col relative z-10">
            {/*Logo*/}
            <div className="p-6 border-b border-slate-200/50 dark:border-slate-700/50 ">
                <div className="flex items-center space-x-3 "> 
                    <div className="w-10 h-10 flex items-center justify-center shadow-lg">
                        <LibraryBig className="w-6 h-6" />
                    </div>
            {/*Conditional Rendering*/}
            <div >
                <h1 className="text-xl front-bold text-slate-1000 dark:text-white ">
                    Degree Path
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400 ">
                    Plan Your Degree!
                </p>
            </div>
                </div>
            </div>
        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto "></nav>
            
        {/*User Profile*/}
        <div className="p-4 border-t border-slate-200/50 dark:border-slate-700/50">   
            <div className="flex items-center space-x-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50">
                <img 
                    src="#" 
                    alt="user" 
                    className="w-10 h-10 rounded-full ring-2 ring-black-500" 
                />
            <div className="flex-1 min-w-0">
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-1000 dark:text-white truncate">John Doe</p>
                    <p className="text-xs text-slate-500 dark:text-slate-500 truncate">john.doe@gmail.com</p>
                </div>
            </div>
            </div>
        </div>
       
    </div> 
    );
}
export default Sidebar;