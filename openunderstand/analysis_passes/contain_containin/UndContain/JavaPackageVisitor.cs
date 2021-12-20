using System.Collections.Generic;
using System.IO;
using System.Linq;
using Antlr4.Runtime.Misc;

namespace UndContain;

public class JavaPackageVisitor : JavaParserLabeledBaseVisitor<string>
{
    private int _lastEntityId;
    private int _lastReferenceId;
    private int NewEntityId => ++_lastEntityId;
    private int NewReferenceId => ++_lastReferenceId;
    private List<JavaTypeDeclaration> JavaTypeDeclarations { get; } = new();
    private List<JavaEntity> JavaEntities { get; } = new();
    private List<JavaReference> JavaReferences { get; } = new();

    public override string VisitCompilationUnit(JavaParserLabeled.CompilationUnitContext context)
    {
        var package = context
            .children
            .OfType<JavaParserLabeled.PackageDeclarationContext>()
            .FirstOrDefault();

        var packageName = package?.children
            .OfType<JavaParserLabeled.QualifiedNameContext>()
            .Select(p => p.GetText())
            .First();

        if (packageName is null)
            return "";
        
        var importDeclaration = GetImportDeclarations(context, packageName);
        JavaTypeDeclarations.AddRange(importDeclaration);

        var classDeclarations = GetClassDeclarations(context, packageName);
        JavaTypeDeclarations.AddRange(classDeclarations);

        var interfaceDeclarations = GetInterfaceDeclarations(context, packageName);
        JavaTypeDeclarations.AddRange(interfaceDeclarations);

        var enumDeclarations = GetEnumDeclarations(context, packageName);
        JavaTypeDeclarations.AddRange(enumDeclarations);

        var annotationTypeDeclarations = GetAnnotationTypeDeclarations(context, packageName);
        JavaTypeDeclarations.AddRange(annotationTypeDeclarations);

        return packageName;
    }

    private IEnumerable<JavaTypeDeclaration> GetImportDeclarations(
        JavaParserLabeled.CompilationUnitContext context, string packageName)
    {
        var importDeclarations = context
            .children
            .OfType<JavaParserLabeled.ImportDeclarationContext>()
            .Where(c => c.children.All(cc => cc.GetText() != "*"))
            .Select(t =>
            {
                var importChunks = t.qualifiedName().GetText().Split('.');
                return new JavaTypeDeclaration
                {
                    Kind = JavaTypeDeclarationKind.FromImport,
                    PackageName = string.Join('.', importChunks[..^1]),
                    Modifier = "",
                    Name = importChunks[^1],
                    Content = "",
                    Line = t.Start.Line,
                    Column = t.Start.Column,
                    FilePath = t.Start.InputStream.SourceName
                };
            });
        return importDeclarations;
    }

    private IEnumerable<JavaTypeDeclaration> GetClassDeclarations(
        JavaParserLabeled.CompilationUnitContext context, string packageName)
    {
        var classDeclarations = context
            .children
            .OfType<JavaParserLabeled.TypeDeclarationContext>()
            .Where(t => t.children.OfType<JavaParserLabeled.ClassDeclarationContext>().Any())
            .Select(t =>
            {
                return new JavaTypeDeclaration
                {
                    Kind = JavaTypeDeclarationKind.Class,
                    PackageName = packageName,
                    Modifier =
                        string.Join(' ',
                            t.children
                                .OfType<JavaParserLabeled.ClassOrInterfaceModifierContext>()
                                .Where(m => m.GetType() != typeof(JavaParserLabeled.AnnotationContext))
                                .Select(m => m.GetText())),

                    Name =
                        t.children
                            .OfType<JavaParserLabeled.ClassDeclarationContext>()
                            .First()
                            .IDENTIFIER()
                            .GetText()!,

                    Content = t.Start.InputStream.GetText(new Interval(t.Start.StartIndex, t.Stop.StopIndex)),
                    Line = t.Start.Line,
                    Column = t.Start.Column,
                    FilePath = t.Start.InputStream.SourceName
                };
            });
        return classDeclarations;
    }

    private IEnumerable<JavaTypeDeclaration> GetInterfaceDeclarations(JavaParserLabeled.CompilationUnitContext context,
        string packageName)
    {
        var interfaceDeclarations = context
            .children
            .OfType<JavaParserLabeled.TypeDeclarationContext>()
            .Where(t => t.children.OfType<JavaParserLabeled.InterfaceDeclarationContext>().Any())
            .Select(t =>
            {
                return new JavaTypeDeclaration
                {
                    Kind = JavaTypeDeclarationKind.Interface,
                    PackageName = packageName,
                    Modifier =
                        string.Join(' ',
                            t.children
                                .OfType<JavaParserLabeled.ClassOrInterfaceModifierContext>()
                                .Where(m => m.GetType() != typeof(JavaParserLabeled.AnnotationContext))
                                .Select(m => m.GetText())),

                    Name =
                        t.children
                            .OfType<JavaParserLabeled.InterfaceDeclarationContext>()
                            .First()
                            .IDENTIFIER()
                            .GetText()!,

                    Content = t.Start.InputStream.GetText(new Interval(t.Start.StartIndex, t.Stop.StopIndex)),
                    Line = t.Start.Line,
                    Column = t.Start.Column,
                    FilePath = t.Start.InputStream.SourceName
                };
            });
        return interfaceDeclarations;
    }

    private IEnumerable<JavaTypeDeclaration> GetEnumDeclarations(JavaParserLabeled.CompilationUnitContext context,
        string packageName)
    {
        var enumDeclarations = context
            .children
            .OfType<JavaParserLabeled.TypeDeclarationContext>()
            .Where(t => t.children.OfType<JavaParserLabeled.EnumDeclarationContext>().Any())
            .Select(t =>
            {
                return new JavaTypeDeclaration
                {
                    Kind = JavaTypeDeclarationKind.Enum,
                    PackageName = packageName,
                    Modifier =
                        string.Join(' ',
                            t.children
                                .OfType<JavaParserLabeled.ClassOrInterfaceModifierContext>()
                                .Where(m => m.GetType() != typeof(JavaParserLabeled.AnnotationContext))
                                .Select(m => m.GetText())),

                    Name =
                        t.children
                            .OfType<JavaParserLabeled.EnumDeclarationContext>()
                            .First()
                            .IDENTIFIER()
                            .GetText()!,

                    Content = t.Start.InputStream.GetText(new Interval(t.Start.StartIndex, t.Stop.StopIndex)),
                    Line = t.Start.Line,
                    Column = t.Start.Column,
                    FilePath = t.Start.InputStream.SourceName
                };
            });
        return enumDeclarations;
    }

    private IEnumerable<JavaTypeDeclaration> GetAnnotationTypeDeclarations(
        JavaParserLabeled.CompilationUnitContext context, string packageName)
    {
        var annotationTypeDeclarations = context
            .children
            .OfType<JavaParserLabeled.TypeDeclarationContext>()
            .Where(t => t.children.OfType<JavaParserLabeled.AnnotationTypeDeclarationContext>().Any())
            .Select(t =>
            {
                return new JavaTypeDeclaration
                {
                    Kind = JavaTypeDeclarationKind.AnnotationType,
                    PackageName = packageName,
                    Modifier =
                        string.Join(' ',
                            t.children
                                .OfType<JavaParserLabeled.ClassOrInterfaceModifierContext>()
                                .Where(m => m.GetType() != typeof(JavaParserLabeled.AnnotationContext))
                                .Select(m => m.GetText())),

                    Name =
                        t.children
                            .OfType<JavaParserLabeled.AnnotationTypeDeclarationContext>()
                            .First()
                            .IDENTIFIER()
                            .GetText()!,

                    Content = t.Start.InputStream.GetText(new Interval(t.Start.StartIndex, t.Stop.StopIndex)),
                    Line = t.Start.Line,
                    Column = t.Start.Column,
                    FilePath = t.Start.InputStream.SourceName
                };
            });
        return annotationTypeDeclarations;
    }

    public IEnumerable<JavaEntity> ExtractEntities()
    {
        var fileEntities =
            JavaTypeDeclarations
                .Select(d => d.FilePath)
                .ToHashSet()
                .Select(f => new JavaEntity
                {
                    Id = NewEntityId,
                    ParentId = null,
                    Name = Path.GetFileName(f),
                    LongName = f,
                    FilePath = f,
                    Contents = File.ReadAllText(f),
                    Kind = "Java File"
                })
                .ToList();

        var knownPackageEntities =
            JavaTypeDeclarations
                .Where(d => d.Kind != JavaTypeDeclarationKind.FromImport)
                .GroupBy(d => d.PackageName)
                .Select(g => g.First())
                .Select(d => new JavaEntity
                {
                    Id = NewEntityId,
                    Name = d.PackageName.Split('.').Last(),
                    LongName = d.PackageName,
                    FilePath = d.FilePath,
                    Contents = null,
                    Package = null,
                    ParentId = fileEntities.First(f => f.FilePath == d.FilePath).Id,
                    Kind = "Java Package"
                })
                .ToList();

        var classEntities =
            JavaTypeDeclarations
                .Where(d => d.Kind == JavaTypeDeclarationKind.Class)
                .Select(d => new JavaEntity
                {
                    Id = NewEntityId,
                    Name = d.Name,
                    LongName = $"{d.PackageName}.{d.Name}",
                    FilePath = d.FilePath,
                    Contents = d.Content,
                    Package = knownPackageEntities.First(p => p.LongName == d.PackageName),
                    ParentId = fileEntities.First(p => p.FilePath == d.FilePath).Id,
                    Kind = EntityKindUtils.GetClassKind(d.Name, d.Modifier),
                    Line = d.Line,
                    Column = d.Column
                })
                .ToList();

        var interfaceEntities =
            JavaTypeDeclarations
                .Where(d => d.Kind == JavaTypeDeclarationKind.Interface)
                .Select(d => new JavaEntity
                {
                    Id = NewEntityId,
                    Name = d.Name,
                    LongName = $"{d.PackageName}.{d.Name}",
                    FilePath = d.FilePath,
                    Contents = d.Content,
                    Package = knownPackageEntities.First(p => p.LongName == d.PackageName),
                    ParentId = fileEntities.First(p => p.FilePath == d.FilePath).Id,
                    Kind = EntityKindUtils.GetInterfaceKind(d.Name, d.Modifier),
                    Line = d.Line,
                    Column = d.Column
                })
                .ToList();

        var enumEntities =
            JavaTypeDeclarations
                .Where(d => d.Kind == JavaTypeDeclarationKind.Enum)
                .Select(d => new JavaEntity
                {
                    Id = NewEntityId,
                    Name = d.Name,
                    LongName = $"{d.PackageName}.{d.Name}",
                    FilePath = d.FilePath,
                    Contents = d.Content,
                    Package = knownPackageEntities.First(p => p.LongName == d.PackageName),
                    ParentId = fileEntities.First(p => p.FilePath == d.FilePath).Id,
                    Kind = EntityKindUtils.GetEnumKind(d.Name, d.Modifier),
                    Line = d.Line,
                    Column = d.Column
                })
                .ToList();

        var interfaceAnnotationEntities =
            JavaTypeDeclarations
                .Where(d => d.Kind == JavaTypeDeclarationKind.AnnotationType)
                .Select(d => new JavaEntity
                {
                    Id = NewEntityId,
                    Name = d.Name,
                    LongName = $"{d.PackageName}.{d.Name}",
                    FilePath = d.FilePath,
                    Contents = d.Content,
                    Package = knownPackageEntities.First(p => p.LongName == d.PackageName),
                    ParentId = fileEntities.First(p => p.FilePath == d.FilePath).Id,
                    Kind = EntityKindUtils.GetAnnotationTypeKind(d.Name, d.Modifier),
                    Line = d.Line,
                    Column = d.Column
                })
                .ToList();

        var unknownEntities =
            JavaTypeDeclarations
                .Where(d => d.Kind == JavaTypeDeclarationKind.FromImport)
                .Where(d => knownPackageEntities.All(p => p.LongName != d.PackageName))
                .GroupBy(d => $"{d.PackageName}.{d.Name}")
                .Select(g => g.First())
                .GroupBy(d => d.PackageName)
                .SelectMany(g =>
                {
                    var package = new JavaEntity
                    {
                        Id = NewEntityId,
                        Name = g.Key.Split('.')[^1],
                        LongName = g.Key,
                        FilePath = g.First().FilePath,
                        Contents = "",
                        Package = null,
                        ParentId = null,
                        Kind = "Java Unknown Package",
                        Line = g.First().Line,
                        Column = g.First().Column
                    };

                    var unknownClasses =
                        g.Select(d => new JavaEntity
                        {
                            Id = NewEntityId,
                            Name = d.Name,
                            LongName = $"{d.PackageName}.{d.Name}",
                            FilePath = d.FilePath,
                            Contents = "",
                            Package = package,
                            ParentId = null,
                            Kind = "Java Unknown Class Type Member",
                            Line = d.Line,
                            Column = d.Column
                        });

                    return new[] {package}.Concat(unknownClasses);
                })
                .ToList();

        var entities =
            fileEntities
                .Concat(knownPackageEntities)
                .Concat(classEntities)
                .Concat(interfaceEntities)
                .Concat(enumEntities)
                .Concat(interfaceAnnotationEntities)
                .Concat(unknownEntities)
                .ToList();

        JavaEntities.Clear();
        JavaEntities.AddRange(entities);
        return JavaEntities;
    }

    public IEnumerable<JavaReference> ExtractReferences()
    {
        var containReferences =
            JavaEntities
                .Where(e =>
                    e.Kind != "Java File"
                    && e.Kind != "Java Package"
                    && e.Kind != "Java Unknown Package")
                .Select(e => new JavaReference
                {
                    Id = NewReferenceId,
                    EntId = e.Id,
                    ScopeId = e.Package!.Id,
                    Line = e.Line!.Value,
                    Column = e.Column!.Value,
                    FileId = JavaEntities.First(je => je.Kind == "Java File" && je.FilePath == e.FilePath).Id,
                    Kind = "Java Contain"
                })
                .ToList();

        var containInReferences =
            containReferences
                .Select(cf => new JavaReference
                {
                    Id = NewReferenceId,
                    EntId = cf.ScopeId,
                    ScopeId = cf.EntId,
                    Line = cf.Line,
                    Column = cf.Column,
                    FileId = cf.FileId,
                    Kind = "Java Containin"
                })
                .ToList();

        var references = containReferences.Concat(containInReferences).ToList();
        JavaReferences.Clear();
        JavaReferences.AddRange(references);
        return JavaReferences;
    }
}