use actix_files as fs;
use actix_web::{web, App, HttpResponse, HttpServer, Result};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Config {
    home_assistant_url: String,
    google_photos_album_ids: Vec<String>,
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
async fn get_photos(_data: web::Data<AppState>) -> Result<HttpResponse> {
    // For now, return a placeholder response
    // In a real implementation, this would fetch from Google Photos API
    // using the album IDs from config
    let photos = vec![
        "https://picsum.photos/1920/1080?random=1",
        "https://picsum.photos/1920/1080?random=2",
        "https://picsum.photos/1920/1080?random=3",
        "https://picsum.photos/1920/1080?random=4",
        "https://picsum.photos/1920/1080?random=5",
    ];
    
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
            google_photos_album_ids: vec![],
            idle_timeout_seconds: 60,
        }
    };
    
    let app_state = web::Data::new(AppState {
        config: Mutex::new(config),
    });
    
    log::info!("Starting server at http://0.0.0.0:8080");
    
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .service(get_config)
            .service(update_config)
            .service(get_photos)
            .service(fs::Files::new("/", "./static").index_file("index.html"))
    })
    .bind(("0.0.0.0", 8080))?
    .run()
    .await
}
