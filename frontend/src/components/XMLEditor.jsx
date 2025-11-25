import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { Eye, Code, Save, Copy, Download, Check } from 'lucide-react';

export function XMLEditor({
    open,
    onOpenChange,
    xmlContent,
    title = "XML Editor",
    onSave,
    readOnly = false
}) {
    const { toast } = useToast();
    const [editedContent, setEditedContent] = useState('');
    const [beautifiedContent, setBeautifiedContent] = useState('');
    const [activeTab, setActiveTab] = useState('formatted');
    const [copied, setCopied] = useState(false);

    const formatXMLWithIndentation = (xml) => {
        const PADDING = '  ';
        const reg = /(>)(<)(\/*)/g;
        let formatted = '';
        let pad = 0;

        xml = xml.replace(reg, '$1\n$2$3');

        const lines = xml.split('\n');
        lines.forEach((node) => {
            let indent = 0;
            if (node.match(/.+<\/\w[^>]*>$/)) {
                indent = 0;
            } else if (node.match(/^<\/\w/) && pad > 0) {
                pad -= 1;
            } else if (node.match(/^<\w[^>]*[^\/]>.*$/)) {
                indent = 1;
            } else {
                indent = 0;
            }

            formatted += PADDING.repeat(pad) + node + '\n';
            pad += indent;
        });

        return formatted.trim();
    };

    const beautifyXML = (xml) => {
        if (!xml) return '';

        try {
            xml = xml.trim();
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xml, 'text/xml');

            const parserError = xmlDoc.querySelector('parsererror');
            if (parserError) {
                console.error('XML parsing error:', parserError.textContent);
                return formatXMLWithIndentation(xml);
            }

            const serializer = new XMLSerializer();
            let formatted = serializer.serializeToString(xmlDoc);
            formatted = formatXMLWithIndentation(formatted);

            return formatted;
        } catch (error) {
            console.error('Error beautifying XML:', error);
            return xml;
        }
    };

    const extractXMLMetadata = (xml) => {
        if (!xml) return {};

        try {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xml, 'text/xml');
            const rootElement = xmlDoc.documentElement;

            if (!rootElement) return {};

            const metadata = {
                rootTag: rootElement.tagName,
                attributes: {},
                childCount: rootElement.children.length,
                size: new Blob([xml]).size,
            };

            for (let i = 0; i < rootElement.attributes.length; i++) {
                const attr = rootElement.attributes[i];
                metadata.attributes[attr.name] = attr.value;
            }

            return metadata;
        } catch (error) {
            return {};
        }
    };

    const syntaxHighlight = (xml) => {
        if (!xml) return '';
        // Return plain XML for now to avoid rendering issues
        return xml.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    };

    useEffect(() => {
        if (xmlContent) {
            setEditedContent(xmlContent);
            setBeautifiedContent(beautifyXML(xmlContent));
        }
    }, [xmlContent]);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(activeTab === 'formatted' ? beautifiedContent : editedContent);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
            toast({
                title: "Copied!",
                description: "XML content copied to clipboard",
            });
        } catch (error) {
            toast({
                title: "Copy Failed",
                description: error.message,
                variant: "destructive"
            });
        }
    };

    const handleDownload = () => {
        const content = activeTab === 'formatted' ? beautifiedContent : editedContent;
        const blob = new Blob([content], { type: 'text/xml' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${title.replace(/\s+/g, '_')}_${new Date().toISOString()}.xml`;
        link.click();
        URL.revokeObjectURL(url);

        toast({
            title: "Downloaded",
            description: "XML file downloaded successfully",
        });
    };

    const handleSave = () => {
        if (onSave) {
            onSave(editedContent);
            toast({
                title: "Saved",
                description: "XML content saved successfully",
            });
        }
    };

    const handleBeautify = () => {
        const beautified = beautifyXML(editedContent);
        setBeautifiedContent(beautified);
        setEditedContent(beautified);
        toast({
            title: "Beautified",
            description: "XML formatted successfully",
        });
    };

    const metadata = extractXMLMetadata(xmlContent);

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Code className="h-5 w-5" />
                        {title}
                    </DialogTitle>
                    <DialogDescription>
                        View and edit XML content with beautified formatting
                    </DialogDescription>
                </DialogHeader>

                {metadata.rootTag && (
                    <div className="grid grid-cols-4 gap-2 p-3 bg-muted rounded-lg text-sm">
                        <div>
                            <span className="font-semibold text-muted-foreground">Root:</span>{' '}
                            <code className="text-xs bg-background px-2 py-1 rounded">{metadata.rootTag}</code>
                        </div>
                        <div>
                            <span className="font-semibold text-muted-foreground">Elements:</span>{' '}
                            <span className="font-mono">{metadata.childCount}</span>
                        </div>
                        <div>
                            <span className="font-semibold text-muted-foreground">Size:</span>{' '}
                            <span className="font-mono">{(metadata.size / 1024).toFixed(2)} KB</span>
                        </div>
                        <div>
                            <span className="font-semibold text-muted-foreground">Format:</span>{' '}
                            <span className="font-mono">XML</span>
                        </div>
                    </div>
                )}

                <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col overflow-hidden">
                    <TabsList className="grid w-full grid-cols-2">
                        <TabsTrigger value="formatted" className="flex items-center gap-2">
                            <Eye className="h-4 w-4" />
                            Formatted View
                        </TabsTrigger>
                        <TabsTrigger value="raw" className="flex items-center gap-2">
                            <Code className="h-4 w-4" />
                            Raw XML
                        </TabsTrigger>
                    </TabsList>

                    <TabsContent value="formatted" className="flex-1 overflow-auto mt-4">
                        <div className="relative">
                            <pre className="bg-slate-950 text-slate-50 p-4 rounded-lg overflow-x-auto text-sm font-mono">
                                <code dangerouslySetInnerHTML={{ __html: syntaxHighlight(beautifiedContent) }} />
                            </pre>
                        </div>
                    </TabsContent>

                    <TabsContent value="raw" className="flex-1 overflow-auto mt-4">
                        {readOnly ? (
                            <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm font-mono whitespace-pre-wrap break-words">
                                {editedContent}
                            </pre>
                        ) : (
                            <textarea
                                className="w-full h-full min-h-[400px] p-4 bg-muted rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                                value={editedContent}
                                onChange={(e) => setEditedContent(e.target.value)}
                                placeholder="Enter XML content..."
                            />
                        )}
                    </TabsContent>
                </Tabs>

                <DialogFooter className="flex items-center justify-between sm:justify-between">
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={handleCopy}>
                            {copied ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
                            {copied ? 'Copied!' : 'Copy'}
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleDownload}>
                            <Download className="h-4 w-4 mr-2" />
                            Download
                        </Button>
                        {!readOnly && (
                            <Button variant="outline" size="sm" onClick={handleBeautify}>
                                <Code className="h-4 w-4 mr-2" />
                                Beautify
                            </Button>
                        )}
                    </div>
                    <div className="flex gap-2">
                        {!readOnly && onSave && (
                            <Button onClick={handleSave}>
                                <Save className="h-4 w-4 mr-2" />
                                Save Changes
                            </Button>
                        )}
                        <Button variant="outline" onClick={() => onOpenChange(false)}>
                            Close
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}

export default XMLEditor;
