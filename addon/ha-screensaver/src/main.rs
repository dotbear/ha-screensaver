use actix_files as fs;
use actix_web::{web, App, HttpResponse, HttpServer, Result};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Config {
    home_assistant_url: String,
    photos_folder: String,
    idle_timeout_seconds: u32,
}

struct AppState {
    config: Mutex<Config>,
}

#[actix_web::get("/api/config")]
async fn get_config(data: web::Data<AppState>) -> Result<HttpResponse> {
    let config = data.config.lock().unwrap();
    Ok(HttpResponse::Ok().json(config.clone()))
}

#[actix_web::post("/api/config")]
async fn update_config(
    data: web::Data<AppState>,
    new_config: web::Json<Config>,
) -> Result<HttpResponse> {
    let mut config = data.config.lock().unwrap();
    *config = new_config.into_inner();
    
    // Save to file
    let config_json = serde_json::to_string_pretty(&*config).unwrap();
    std::fs::write("config.json", config_json).unwrap();
    
    Ok(HttpResponse::Ok().json(&*config))
}

#[actix_web::get("/api/photos")]
async fn get_photos(data: web::Data<AppState>) -> Result<HttpResponse> {
    let config = data.config.lock().unwrap();
    let photos_folder = config.photos_folder.clone();
    drop(config);
    
    // Scan the photos folder for image files
    let mut photos = Vec::new();
    
    if let Ok(entries) = std::fs::read_dir(&photos_folder) {
        for entry in entries.flatten() {
            if let Ok(path) = entry.path().canonicalize() {
                if let Some(extension) = path.extension() {
                    let ext = extension.to_string_lossy().to_lowercase();
                    if matches!(ext.as_ref(), "jpg" | "jpeg" | "png" | "gif" | "webp") {
                        // Convert absolute path to relative URL
                        if let Some(filename) = path.file_name() {
                            photos.push(format!("/photos/{}", filename.to_string_lossy()));
                        }
                    }
                }
            }
        }
    }
    
    log::info!("Found {} photos in {}", photos.len(), photos_folder);
    Ok(HttpResponse::Ok().json(photos))
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init_from_env(env_logger::Env::new().default_filter_or("info"));
    
    // Load or create config
    let config = if std::path::Path::new("config.json").exists() {
        let config_str = std::fs::read_to_string("config.json").unwrap();
        serde_json::from_str(&config_str).unwrap()
    } else {
        Config {
            home_assistant_url: "http://homeassistant.local:8123".to_string(),
            photos_folder: "./photos".to_string(),
            idle_timeout_seconds: 60,
        }
    };
    
    // Create photos folder if it doesn't exist
    std::fs::create_dir_all(&config.photos_folder).ok();

    let app_state = web::Data::new(AppState {
        config: Mutex::new(config.clone()),
    });
    
    log::info!("Starting server at http://0.0.0.0:8080");
    log::info!("Photos folder: {}", config.photos_folder);
    
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(get_config)
            .service(update_config)
            .service(get_photos)
            .service(fs::Files::new("/photos", &config.photos_folder).show_files_listing())
            .service(fs::Files::new("/", "./static").index_file("index.html"))
    })
    .bind(("0.0.0.0", 8080))?
    .run()
    .await
}
