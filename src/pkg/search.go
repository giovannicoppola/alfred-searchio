//
// Copyright (c) 2017 Dean Jackson <deanishe@deanishe.net>
//
// MIT Licence. See http://opensource.org/licenses/MIT
//
// Created on 2017-12-11
//

// Command search performs a web search based on a Searchio! search.
package main

import (
	"compress/gzip"
	"crypto/md5"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"golang.org/x/net/html/charset"

	"github.com/JumboInteractiveLimited/jsonpath"
	aw "github.com/deanishe/awgo"
	"github.com/deanishe/awgo/util"
)

var (
	maxAge                = time.Second * 900
	queryInResults        bool // Also add query to results
	alfredSortsResults    bool // Turn off UIDs
	searchID, query       string
	searchesDir, cacheDir string
	// HTTPTimeout is the timeout for establishing an HTTP(S) connection.
	HTTPTimeout = (60 * time.Second)
	wf          *aw.Workflow
)

// installDefaultSearchesIfNeeded installs default search configurations if the searches directory is empty
func installDefaultSearchesIfNeeded() {
	// Check if searches directory exists and is empty
	if _, err := os.Stat(searchesDir); os.IsNotExist(err) {
		// Create searches directory
		if err := os.MkdirAll(searchesDir, 0755); err != nil {
			log.Printf("Failed to create searches directory: %v", err)
			return
		}
	}

	// Check if directory is empty
	files, err := ioutil.ReadDir(searchesDir)
	if err != nil {
		log.Printf("Failed to read searches directory: %v", err)
		return
	}

	// If directory is not empty, don't install defaults
	if len(files) > 0 {
		return
	}

	// Install default searches
	defaultSearches := []string{"google-en", "wikipedia-en", "youtube-us"}
	workflowDir := wf.Dir()

	for _, searchID := range defaultSearches {
		srcPath := filepath.Join(workflowDir, "default_searches", searchID+".json")
		dstPath := filepath.Join(searchesDir, searchID+".json")

		// Copy default search file
		if err := copyFile(srcPath, dstPath); err != nil {
			log.Printf("Failed to install default search %s: %v", searchID, err)
			continue
		}
		log.Printf("Installed default search: %s", searchID)
	}

	// Icon paths are now set directly in Script Filter config, no symlinks needed
	// createIconSymlinks()
}

// createIconSymlinks creates symlinks for Script Filter icons
func createIconSymlinks() {
	workflowDir := wf.Dir()
	log.Printf("Creating icon symlinks in workflow directory: %s", workflowDir)

	// Define icon mappings for default searches
	iconMappings := map[string]string{
		"google-en":    "icons/engines/google.png",
		"wikipedia-en": "icons/engines/wikipedia.png",
		"youtube-us":   "icons/engines/youtube.png",
	}

	for searchID, iconPath := range iconMappings {
		// Check if source icon exists
		srcPath := filepath.Join(workflowDir, iconPath)
		if _, err := os.Stat(srcPath); os.IsNotExist(err) {
			log.Printf("Warning: Source icon does not exist: %s", srcPath)
			continue
		}

		// Remove existing symlink if it exists
		symlinkPath := filepath.Join(workflowDir, searchID+".png")
		if _, err := os.Lstat(symlinkPath); err == nil {
			if err := os.Remove(symlinkPath); err != nil {
				log.Printf("Failed to remove existing symlink %s: %v", symlinkPath, err)
			}
		}

		// Create symlink
		if err := os.Symlink(iconPath, symlinkPath); err != nil {
			log.Printf("Failed to create icon symlink for %s: %v", searchID, err)
			continue
		}
		log.Printf("Successfully created icon symlink: %s.png -> %s", searchID, iconPath)

		// Verify the symlink was created
		if _, err := os.Lstat(symlinkPath); err != nil {
			log.Printf("Warning: Symlink verification failed for %s: %v", symlinkPath, err)
		} else {
			log.Printf("Verified symlink exists: %s", symlinkPath)
		}
	}
}

// copyFile copies a file from src to dst
func copyFile(src, dst string) error {
	sourceFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer sourceFile.Close()

	destFile, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer destFile.Close()

	_, err = io.Copy(destFile, sourceFile)
	return err
}

func init() {
	wf = aw.New()
	queryInResults = wf.Config.GetBool("SHOW_QUERY_IN_RESULTS")
	alfredSortsResults = wf.Config.GetBool("ALFRED_SORTS_RESULTS")
	searchesDir = filepath.Join(wf.DataDir(), "searches")

	if !alfredSortsResults {
		wf.Configure(aw.SuppressUIDs(true))
	}

	// Install default searches if searches directory is empty
	installDefaultSearchesIfNeeded()
}

// GetenvBool returns a boolean based on an environment/workflow variable.
// "1", "yes" = true, "0", "no", empty = false
func GetenvBool(key string) bool {
	s := strings.ToLower(os.Getenv(key))
	switch s {
	case "":
		return false
	case "0":
		return false
	case "no":
		return false
	case "1":
		return true
	case "yes":
		return true
	}
	log.Printf("[WARNING] don't understand value \"%s\" for \"%s\", returning false", s, key)
	return false
}

// Search is a Searchio! search configuration.
type Search struct {
	Icon          string `json:"icon"`
	Jsonpath      string `json:"jsonpath"`
	Keyword       string `json:"keyword"`
	PercentEncode bool   `json:"pcencode"`
	SearchURL     string `json:"search_url"`
	SuggestURL    string `json:"suggest_url"`
	Title         string `json:"title"`
	UID           string `json:"uid"`
}

// SearchURLForQuery returns a URL for query based on SearchURL template.
func (s *Search) SearchURLForQuery(q string) string { return s.makeURL(q, s.SearchURL) }

// SuggestURLForQuery returns a URL for query based on SuggestURL template.
func (s *Search) SuggestURLForQuery(q string) string { return s.makeURL(q, s.SuggestURL) }

// Escape query as path or query string depending on Search.PercentEncode.
func (s *Search) escapeQuery(q string) string {
	if s.PercentEncode {
		return url.PathEscape(q)
	} else {
		return url.QueryEscape(q)
	}
}

func (s *Search) makeURL(q, baseURL string) string {
	q = s.escapeQuery(q)
	u := strings.Replace(baseURL, "{query}", q, -1)
	// Also replace envvars
	return os.Expand(u, func(key string) string { return s.escapeQuery(os.Getenv(key)) })
}

// makeHTTPClient returns an http.Client with a sensible configuration.
func makeHTTPClient() http.Client {
	return http.Client{
		Transport: &http.Transport{
			Dial: (&net.Dialer{
				Timeout:   HTTPTimeout,
				KeepAlive: HTTPTimeout,
			}).Dial,
			TLSHandshakeTimeout:   30 * time.Second,
			ResponseHeaderTimeout: 30 * time.Second,
			ExpectContinueTimeout: 10 * time.Second,
		},
	}
}

// Load a search from the corresponding configuration file in the searches directory.
func loadSearch(id string) (*Search, error) {
	p := filepath.Join(searchesDir, id+".json")
	log.Printf("loading search from %s ...", p)
	b, err := ioutil.ReadFile(p)
	if err != nil {
		return nil, err
	}
	s := &Search{}
	if err := json.Unmarshal(b, &s); err != nil {
		return nil, err
	}
	s.UID = id
	return s, nil
}

func decodeResponse(r *http.Response) ([]byte, error) {
	var reader io.Reader = r.Body

	// Handle gzip compression
	if r.Header.Get("Content-Encoding") == "gzip" {
		gzReader, err := gzip.NewReader(r.Body)
		if err != nil {
			return nil, fmt.Errorf("failed to create gzip reader: %v", err)
		}
		defer gzReader.Close()
		reader = gzReader
	}

	data, err := ioutil.ReadAll(reader)
	if err != nil {
		return nil, err
	}

	// Handle character encoding
	enc, name, ok := charset.DetermineEncoding(data, r.Header.Get("Content-Type"))
	log.Printf("enc=%v, name=%s, ok=%v", enc, name, ok)

	data, err = enc.NewDecoder().Bytes(data)
	if err != nil {
		return nil, err
	}
	return data, nil
}

// Query server.
func searchServer(s *Search, q string) ([]string, error) {
	var (
		client = makeHTTPClient()
		u      = s.SuggestURLForQuery(q)
		words  = []string{}
	)

	// Create request with proper headers
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return nil, err
	}

	// Set User-Agent and other headers for Wikipedia API compatibility
	req.Header.Set("User-Agent", "Alfred-Searchio-Workflow/1.40.0 (https://github.com/giovannicoppola/alfred-searchio; giovanni@example.com)")
	req.Header.Set("Accept", "application/json, text/plain, */*")
	req.Header.Set("Accept-Language", "en-US,en;q=0.9")
	req.Header.Set("Accept-Encoding", "gzip, deflate")

	r, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer r.Body.Close()
	log.Printf("[%d] %s", r.StatusCode, r.Status)

	if r.StatusCode > 299 {
		return nil, fmt.Errorf("[%d] %s", r.StatusCode, r.Status)
	}

	data, err := decodeResponse(r)
	if err != nil {
		return nil, err
	}

	// Log the response data for debugging
	log.Printf("Response data length: %d", len(data))
	if len(data) < 200 {
		log.Printf("Response data: %s", string(data))
	} else {
		log.Printf("Response data (first 200 chars): %s", string(data[:200]))
	}

	// Append + as we want to extract a value, not a path
	jp := s.Jsonpath
	if jp == "" {
		// If no JSON path is specified, return empty suggestions
		return []string{}, nil
	}
	if jp[len(jp)-1] != '+' {
		jp += "+"
	}
	paths, err := jsonpath.ParsePaths(jp)
	if err != nil {
		return nil, fmt.Errorf("bad JSON path: %v", err)
	}

	eval, err := jsonpath.EvalPathsInBytes(data, paths)
	if err != nil {
		// Try to parse as plain JSON first to see if it's valid JSON
		var testJSON interface{}
		if jsonErr := json.Unmarshal(data, &testJSON); jsonErr != nil {
			return nil, fmt.Errorf("Invalid JSON response: %v (original error: %v)", jsonErr, err)
		}
		return nil, fmt.Errorf("JSON path evaluation error: %v", err)
	}

	for {
		r, ok := eval.Next()
		if !ok {
			break
		}
		if r != nil {
			var word string
			if err := json.Unmarshal(r.Value, &word); err != nil {
				return nil, err
			}
			words = append(words, word)
		}
	}
	if eval.Error != nil {
		return nil, fmt.Errorf("couldn't unmarshal JSON: %v", eval.Error)
	}

	return words, nil
}

// Perform search and show results in Alfred.
func doSearch(s *Search, q string) error {
	var (
		h      = fmt.Sprintf("%x", md5.Sum([]byte(q)))
		reldir = fmt.Sprintf("searches/%s/%s/%s", s.UID, h[:2], h[2:4])
		name   = fmt.Sprintf("%s/%s.json", reldir, h)
		words  = []string{}
	)
	util.MustExist(filepath.Join(wf.CacheDir(), reldir))

	log.Printf(`querying "%s" for "%s" ...`, s.Title, q)
	reload := func() (interface{}, error) { return searchServer(s, q) }
	if err := wf.Cache.LoadOrStoreJSON(name, maxAge, reload, &words); err != nil {
		return err
	}

	log.Printf(`%d results for "%s"`, len(words), q)

	// Send results to Alfred
	var (
		// querySeen bool
		icon = &aw.Icon{Value: s.Icon}
	)
	for _, word := range words {
		if strings.EqualFold(word, q) && !queryInResults {
			continue
		}
		URL := s.SearchURLForQuery(word)
		wf.NewItem(word).
			Subtitle(s.Title).
			Autocomplete(word + " ").
			Arg(URL).
			UID(URL).
			Icon(icon).
			Valid(true)
	}

	// Add query at end of results
	if queryInResults || len(words) == 0 {
		URL := s.SearchURLForQuery(q)
		wf.NewItem(q).
			Subtitle(s.Title).
			Autocomplete(q + " ").
			Arg(URL).
			UID(URL).
			Icon(icon).
			Valid(true)
	}

	wf.WarnEmpty("No Results", "Try a different query?")
	wf.SendFeedback()
	return nil
}

// Entry point.
func run() {
	argv := wf.Args()
	if len(argv) < 2 {
		log.Fatalln("usage: search <search> <query>")
	}
	searchID, query = argv[0], argv[1]
	s, err := loadSearch(searchID)
	if err != nil {
		wf.FatalError(err)
	}

	if err := doSearch(s, query); err != nil {
		wf.FatalError(err)
	}
}

// Run via Workflow.Run to catch panics.
func main() {
	wf.Run(run)
}
