pipeline {
    agent any
    
    stages {
        stage('Stage 1: Clone Repository') {
            steps {
                script {
                    // Specify the path where you want to clone the repository
                    def repoPath = "C:\\Users\\sansk\\OneDrive\\Desktop\\StaticCodeAnalysis"
                    
                    // Clone the repository
                    git branch: 'master', credentialsId: '65fd2953-20c8-47ac-90a5-6de4ab6edf5a', url: 'https://github.com/sanskar22003/GreenCodeScan.git', dir: repoPath
                }
            }
        }
        
        stage('Stage 2: Static Source Code Analysis using GitHub Copilot Plugin Installed in Neovim Editor') {
            steps {
                script {
                    // Define paths
                    def sourceFolder = "C:\\Users\\sansk\\OneDrive\\Desktop\\StaticCodeAnalysis"
                    def destinationFolder = "C:\\Users\\sansk\\OneDrive\\Desktop\\StaticCodeAnalysis\\destination_folder"
                    def promptsFile = "C:\\Code\\GreenCodeApi\\prompts.csv"
                    
                    // Iterate over each file in the source folder
                    sh "mkdir ${destinationFolder}"
                    sh "cp -r ${sourceFolder} ${destinationFolder}" // Copy source files to destination folder
                    
                    // Apply prompts using GitHub Copilot in Neovim
                    sh "nvim --headless -c 'source ${promptsFile}' -c 'CocCommand copilot.applyPrompt'"
                }
            }
        }
        
        stage('Stage 3: Running Unit Test Cases') {
            steps {
                script {
                    // Install pytest if not installed
                    sh "pip install pytest"
                    
                    // Run pytest in test folder
                    sh "pytest C:\\Users\\sansk\\OneDrive\\Desktop\\StaticCodeAnalysis\\tests"
                }
            }
        }
        
        stage('Stage 4: Storing Emission Data') {
            steps {
                script {
                    // Run codecarbon to track emissions
                    sh "codecarbon --output-path C:\\Users\\sansk\\OneDrive\\Desktop\\StaticCodeAnalysis\\emission_data.csv"
                }
            }
        }
    }
}
