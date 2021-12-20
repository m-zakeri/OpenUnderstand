﻿using System;
using System.IO;

namespace UndContain;

public static class Program
{
    public static void Main(string[] args)
    {
        var projectPath = Path.GetFullPath(args[0]);
        if (!Directory.Exists(projectPath))
        {
            Console.WriteLine("Project path is invalid");
            return;
        }

        var dbPath = Path.GetFullPath(args[1]);
        if (!File.Exists(dbPath))
        {
            Console.WriteLine("Db file path is invalid");
            return;
        }

        var explorer = new JavaExplorer(projectPath);
        explorer.ExplorePackages();
        explorer.ExportToDb($"Data Source={dbPath};");
    }
}